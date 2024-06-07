import sys
import tkinter as tk
from tkinter import ttk, messagebox
import win32gui
import win32ui
import win32con
import win32api
import win32com.client
from PIL import Image
import io
import requests
import time
import os
import subprocess

def get_token(host, username, password):
    response = requests.post(host + '/login', json={'username': username, 'password': password})
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print('Failed to obtain JWT token:', response.json().get('msg', 'Unknown error'))
        exit(1)

def register_user(host, username, password):
    response = requests.post(host + '/register', json={'username': username, 'password': password})
    if response.status_code == 200:
        return True
    else:
        print('Failed to register:', response.json().get('msg', 'Unknown error'))
        return False

def main(host, key, token):
    headers = {'Authorization': f'Bearer {token}'}

    r = requests.post(host + '/new_sessions', json={'_key': key}, headers=headers)
    if r.status_code != 200:
        print('Server not available.')
        return

    shell = win32com.client.Dispatch('WScript.Shell')
    PREV_IMG = None
    while True:
        hdesktop = win32gui.GetDesktopWindow()

        width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)


        desktop_dc = win32gui.GetWindowDC(hdesktop)
        img_dc = win32ui.CreateDCFromHandle(desktop_dc)


        mem_dc = img_dc.CreateCompatibleDC()

        screenshot = win32ui.CreateBitmap()
        screenshot.CreateCompatibleBitmap(img_dc, width, height)
        mem_dc.SelectObject(screenshot)

        bmpinfo = screenshot.GetInfo()


        mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top), win32con.SRCCOPY)

        bmpstr = screenshot.GetBitmapBits(True)

        pillow_img = Image.frombytes('RGB',
                                     (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                                     bmpstr, 'raw', 'BGRX')

        with io.BytesIO() as image_data:
            pillow_img.save(image_data, 'PNG')
            image_data_content = image_data.getvalue()

        if image_data_content != PREV_IMG:
            files = {}
            filename = str(round(time.time() * 1000)) + '_' + key
            files[filename] = ('img.png', image_data_content, 'multipart/form-data')

            try:
                r = requests.post(host + '/capture_post', files=files, headers=headers)
            except Exception as e:
                pass

            PREV_IMG = image_data_content
        else:
            pass


        try:
            r = requests.post(host + '/execute_events', json={'_key': key}, headers=headers)
            data = r.json()
            for e in data['events']:
                print(e)

                if e['type'] == 'click':
                    win32api.SetCursorPos((e['x'], e['y']))
                    time.sleep(0.1)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, e['x'], e['y'], 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, e['x'], e['y'], 0, 0)

                if e['type'] == 'keydown':
                    cmd = ''

                    if e['shiftKey']:
                        cmd += '+'

                    if e['ctrlKey']:
                        cmd += '^'

                    if e['altKey']:
                        cmd += '%'

                    if len(e['key']) == 1:
                        cmd += e['key'].lower()
                    else:
                        cmd += '{' + e['key'].upper() + '}'

                    print(cmd)
                    shell.SendKeys(cmd)

        except Exception as err:
            print(err)
            pass


        mem_dc.DeleteDC()
        win32gui.DeleteObject(screenshot.GetHandle())
        time.sleep(0.2)

def on_submit():
    addr = entry_addr.get()
    key = entry_key.get()
    username = entry_username.get()
    password = entry_password.get()

    try:
        token = get_token(addr, username, password)
        root.destroy()
        main(addr, key, token)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def on_register():
    addr = entry_addr.get()
    username = entry_username.get()
    password = entry_password.get()

    try:
        success = register_user(addr, username, password)
        if success:
            messagebox.showinfo("Success", "User registered successfully")
        else:
            messagebox.showerror("Error", "User registration failed")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def add_to_startup():
    exe_path = os.path.abspath(__file__)
    command = f'reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v MyApp /t REG_SZ /d "{exe_path}" /f'
    try:
        subprocess.run(command, shell=True, check=True)
        print("Added to startup successfully.")
    except subprocess.CalledProcessError as e:
        print("Error adding to startup:", e)

def toggle_startup():
    if startup_var.get():
        add_to_startup()
    else:
        remove_from_startup()

def remove_from_startup():
    command = 'reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v MyApp /f'
    try:
        subprocess.run(command, shell=True, check=True)
        print("Removed from startup successfully.")
    except subprocess.CalledProcessError as e:
        print("Error removing from startup:", e)

root = tk.Tk()
root.title("rgz")

style = ttk.Style()
style.configure('TButton', foreground='green', background='lightgray', font=('Helvetica', 12))
style.configure('TLabel', foreground='blue', font=('Helvetica', 14))
style.configure('TEntry', font=('Helvetica', 12))

tk.Label(root, text="Server Address", font=('Helvetica', 14)).grid(row=0, column=0, sticky='ew', padx=10, pady=5)
tk.Label(root, text="Access Key", font=('Helvetica', 14)).grid(row=1, column=0, sticky='ew', padx=10, pady=5)
tk.Label(root, text="Username", font=('Helvetica', 14)).grid(row=2, column=0, sticky='ew', padx=10, pady=5)

tk.Label(root, text="Password", font=('Helvetica', 14)).grid(row=3, column=0, sticky='ew', padx=10, pady=5)

entry_addr = ttk.Entry(root)
entry_addr.insert(0, "http://217.71.129.139:4317")
entry_key = ttk.Entry(root)
entry_username = ttk.Entry(root)
entry_password = ttk.Entry(root, show="*")

style.configure('Custom.TButton', foreground='green', background='lightgray', font=('Helvetica', 12), relief='raised')
style.map('Custom.TButton', background=[('active', 'lightgreen')])

submit_button = ttk.Button(root, text="Login", command=on_submit, style='Custom.TButton')
submit_button.grid(row=4, column=0, columnspan=2, sticky='ew', pady=10)

register_button = ttk.Button(root, text="Register", command=on_register, style='Custom.TButton')
register_button.grid(row=5, column=0, columnspan=2, sticky='ew', pady=10)

entry_addr.grid(row=0, column=1, sticky='ew', padx=10, pady=5)
entry_key.grid(row=1, column=1, sticky='ew', padx=10, pady=5)
entry_username.grid(row=2, column=1, sticky='ew', padx=10, pady=5)
entry_password.grid(row=3, column=1, sticky='ew', padx=10, pady=5)

submit_button = ttk.Button(root, text="Login", command=on_submit)
submit_button.grid(row=4, column=0, columnspan=2, sticky='ew', pady=10)

register_button = ttk.Button(root, text="Register", command=on_register)
register_button.grid(row=5, column=0, columnspan=2, sticky='ew', pady=10)

startup_var = tk.BooleanVar()
startup_checkbox = ttk.Checkbutton(root, text="Start with Windows", variable=startup_var)
startup_checkbox.grid(row=6, column=0, columnspan=2, sticky='ew', pady=5)
startup_checkbox.invoke()  # Automatically checks the checkbox


startup_var.trace_add("write", lambda name, index, mode, var=startup_var: toggle_startup())


for child in root.winfo_children():
    child.grid_configure(padx=5, pady=5)

separator = ttk.Separator(root, orient='horizontal')
separator.grid(row=7, column=0, columnspan=2, sticky='ew', pady=10)

footer_label = ttk.Label(root, text="github.com/DisstressZ", font=('Helvetica', 10), foreground='gray')
footer_label.grid(row=8, column=0, columnspan=2, sticky='ew', pady=5)

root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(8, weight=1)

root.mainloop()


def add_to_startup():

    script_dir = os.path.dirname(os.path.abspath(__file__))

    exe_path = os.path.join(script_dir, "Remote.exe")


    command = f'reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v MyApp /t REG_SZ /d "{exe_path}" /f'

    try:

        subprocess.run(command, shell=True, check=True)
        print("Добавлено в автозапуск успешно.")
    except subprocess.CalledProcessError as e:
        print("Ошибка добавления в автозапуск:", e)

def toggle_startup():
    if startup_var.get():
        add_to_startup()
    else:
        remove_from_startup()

def remove_from_startup():
    command = 'reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v MyApp /f'
    try:
        subprocess.run(command, shell=True, check=True)
        print("Removed from startup successfully.")
    except subprocess.CalledProcessError as e:
        print("Error removing from startup:", e)