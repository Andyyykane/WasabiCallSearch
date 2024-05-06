import pyodbc
import os
import sys
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from PIL import Image, ImageTk
import re
import vlc
import logging
import tempfile
import tkinter.messagebox as messagebox
from PIL import Image, ImageTk
from datetime import datetime, timedelta
from datetime import datetime, date
import json
import boto3
import keyring

vlc_player = vlc.MediaPlayer()
current_date = datetime.now().strftime("%Y%m%d")
LOG_FILENAME = f"Debug_{current_date}.log"

class ToolTip:
    def __init__(self, widget, text="Tooltip text"):
        self.waittime = 500     
        self.wraplength = 180   
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.onEnter)
        self.widget.bind("<Leave>", self.onLeave)
        self.tooltipwindow = None

    def onEnter(self, event=None):
        self.schedule = self.widget.after(self.waittime, self.showTooltip)

    def onLeave(self, event=None):
        self.widget.after_cancel(self.schedule)
        self.hideTooltip()

    def showTooltip(self):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

    
        self.tooltipwindow = tk.Toplevel(self.widget)
        
        self.tooltipwindow.wm_overrideredirect(True)
        self.tooltipwindow.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltipwindow, text=self.text, justify='left',
                          background='white', relief=
                          'solid', borderwidth=1,
                          wraplength=self.wraplength)
        label.pack()

    def hideTooltip(self):
        if self.tooltipwindow:
            self.tooltipwindow.destroy()

class LoggerWriter:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''
    
    def write(self, message):
        for line in message.splitlines():
            if line:
                self.logger.log(self.level, line.rstrip())
    
    def flush(self):
        pass

def setup_logging(enable_logging):
    if enable_logging:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_directory = "C:/RecordingSearchLogs"
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)
        log_filename = os.path.join(log_directory, f"Debug_{current_time}.log")
        logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        sys.stdout = LoggerWriter(logging.getLogger(), logging.INFO)
        sys.stderr = LoggerWriter(logging.getLogger(), logging.ERROR)

def load_settings():
    default_settings = {
        "SQL": {
            "Driver": "ODBC Driver 17 for SQL Server",
            "Server": " ",
            "Database": " ",
            "Trusted_Connection": "yes"
        },
        "S3": {
            "ServiceURL": " ",
            "AccessKey": " ",
            "SecretKey": " ",
            "BucketName": " "
        },
        "SQL_Tables": [
            "Connex1",
            "F9CRMigRecordings",
            "F9CRMigUploads",
            "F9CROSPVoice",
            "F9CRUploads",
            "OSPVoice",
            "Recordings",
            "Uploads"
        ],
        "enable_logging": False,
        "DefaultSaveLocation": "C:/default/path"
    }

    settings_path = 'C:\\programdata\\callrecordingsearch\\CallSearchConfig.json'
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as file:
                settings = json.load(file)
                return settings
        except json.JSONDecodeError:
            print("Error reading the settings file. Using default settings.")
    return default_settings

def save_settings(settings):
    settings_directory = 'C:\\programdata\\callrecordingsearch'
    settings_file_path = os.path.join(settings_directory, 'CallSearchConfig.json')

    if not os.path.exists(settings_directory):
        try:
            os.makedirs(settings_directory)
        except Exception as e:
            print(f"Failed to create settings directory: {e}")
            return  
    try:
        with open(settings_file_path, 'w') as file:
            json.dump(settings, file, indent=4)
        print("Settings saved successfully.")
    except Exception as e:
        print(f"Failed to save settings: {e}")

DEFAULT_SETTINGS = {
    "SQL": {
        "Driver": "ODBC Driver 17 for SQL Server",
        "Server": "SQL Server Hostname",
        "Database": "SQL Database",
        "Trusted_Connection": "yes"
    },
    "S3": {
        "ServiceURL": "Your S3 Service URL",
        "AccessKey": "YourWasabiAccessKey",
        "SecretKey": "YourWasabiSecretKey",
        "BucketName": "YourBucketName"
    },
    "SQL_Tables": [
        "Connex1",
        "F9CRMigRecordings",
        "F9CRMigUploads",
        "F9CROSPVoice",
        "F9CRUploads",
        "OSPVoice",
        "Recordings",
        "Uploads"
    ],
    "enable_logging": False,
    "DefaultSaveLocation": "C:/default/path"
}

settings = load_settings()
if settings is None:
    settings = DEFAULT_SETTINGS
if "enable_logging" not in settings:
    settings["enable_logging"] = False 

if settings["enable_logging"]:
    setup_logging(settings["enable_logging"])


CONNECTION_STRING = f"""
Driver={{{settings["SQL"]["Driver"]}}};
Server={{{settings["SQL"]["Server"]}}};
Database={{{settings["SQL"]["Database"]}}};
Trusted_Connection={{{settings["SQL"]["Trusted_Connection"]}}};
"""

def sanitize_filename(filename):
    return re.sub(r'[\\/:"*?<>|]+', "_", filename)

def download_file_from_wasabi(wasabi_path, local_directory, filename):
    wasabi_client = create_wasabi_client()
    local_path = os.path.join(local_directory, filename)
    os.makedirs(local_directory, exist_ok=True)  

    print(f"[DEBUG] Downloading from Wasabi Path: {wasabi_path} to Local Path: {local_path}")

    try:
        with open(local_path, 'wb') as file:
            wasabi_client.download_fileobj(settings["S3"]["BucketName"], wasabi_path, file)
        print(f"Successfully downloaded: {filename}")
    except Exception as e:
        print(f"Error downloading file from Wasabi: {str(e)}")

def create_wasabi_client():
    access_key = keyring.get_password("callrecordingsearch", "wasabi_access_key")
    secret_key = keyring.get_password("callrecordingsearch", "wasabi_secret_key")

    if not access_key or not secret_key:
        raise Exception("Wasabi credentials not found in Credential Manager.")

    wasabi_client = boto3.client(
        's3',
        endpoint_url=settings["S3"]["ServiceURL"],  
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1'  
    )

    try:
        wasabi_client.list_buckets()
        print("Wasabi connection test successful.")
    except Exception as e:
        print(f"Error testing Wasabi connection: {str(e)}")

    return wasabi_client


def select_copy_to_dir(entry_widget):
    initial_dir = settings.get("DefaultSaveLocation", "") 
    
    directory = filedialog.askdirectory(initialdir=initial_dir)  
    if directory:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, directory)       


def open_settings_window():
    global server_entry, database_entry, s3_service_url_entry, s3_access_key_entry, s3_secret_key_entry, s3_bucket_name_entry, default_save_location_entry

    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("400x800")
    settings_window.configure(bg="white")

    def save_settings_and_close():
        settings["SQL"] = {
            "Driver": "ODBC Driver 17 for SQL Server",
            "Server": server_entry.get(),
            "Database": database_entry.get(),
            "Trusted_Connection": "yes"
        }
        settings["S3"] = {
            "ServiceURL": s3_service_url_entry.get(),
            "BucketName": s3_bucket_name_entry.get()
        }
        settings["enable_logging"] = enable_logging_var.get()
        settings["DefaultSaveLocation"] = default_save_location_entry.get()

        s3_access_key = s3_access_key_entry.get()
        s3_secret_key = s3_secret_key_entry.get()
        if s3_access_key != "•" and s3_secret_key != "•••••••":
            keyring.set_password("callrecordingsearch", "wasabi_access_key", s3_access_key)
            keyring.set_password("callrecordingsearch", "wasabi_secret_key", s3_secret_key)
        
        enable_logging = enable_logging_var.get()
        if enable_logging_var.get():
           setup_logging(enable_logging)

        save_settings(settings) 
        settings_window.destroy()

    def load_current_settings():
        server_entry.insert(0, settings["SQL"]["Server"])
        database_entry.insert(0, settings["SQL"]["Database"])
        if "S3" in settings:
            s3_service_url_entry.insert(0, settings["S3"].get("ServiceURL", ""))
            s3_access_key = settings["S3"].get("wasabi_access_key", "")
            s3_secret_key = settings["S3"].get("wasabi_secret_key", "")
            if s3_access_key:
                s3_access_key_entry.insert(0, s3_access_key)
            else:
                s3_access_key_entry.insert(0, "•••••••")
            if s3_secret_key:
                s3_secret_key_entry.insert(0, s3_secret_key)
            else:
                s3_secret_key_entry.insert(0, "•••••••")
            s3_bucket_name_entry.insert(0, settings["S3"].get("BucketName", ""))
        if "DefaultSaveLocation" in settings:
            default_save_location_entry.insert(0, settings["DefaultSaveLocation"])

        enable_logging_var.set(settings.get("enable_logging", False))

    settings_frame = tk.Frame(settings_window, bg="white")
    settings_frame.pack()

    tk.Label(settings_frame, text="SQL Settings", bg="white", font=("Arial", 14)).pack(pady=10)
    tk.Label(settings_frame, text="Server:", bg="white", font=("Arial", 12)).pack(anchor="w", padx=20)
    server_entry = tk.Entry(settings_frame, width=30, font=("Arial", 10))
    server_entry.pack(padx=20)
    tk.Label(settings_frame, text="Database:", bg="white", font=("Arial", 12)).pack(anchor="w", padx=20)
    database_entry = tk.Entry(settings_frame, width=30, font=("Arial", 10))
    database_entry.pack(padx=20)
    tk.Button(settings_frame, text="Test SQL Connection", command=test_sql_connection, bg="#70b966", fg="white", relief=tk.RAISED, font=("Arial", 10)).pack(pady=10)

    tk.Label(settings_frame, text="S3 Settings", bg="white", font=("Arial", 14)).pack(pady=10)
    s3_service_url_entry = create_entry_with_label(settings_frame, "S3 Service URL:")
    s3_access_key_entry = create_entry_with_label(settings_frame, "S3 Access Key:", show_text='•')
    s3_secret_key_entry = create_entry_with_label(settings_frame, "S3 Secret Key:", show_text='•')
    s3_bucket_name_entry = create_entry_with_label(settings_frame, "S3 Bucket Name:")

    enable_logging_var = tk.BooleanVar(value=settings.get("enable_logging", False))
    tk.Checkbutton(settings_frame, text="Enable logging", variable=enable_logging_var, bg="white", font=("Arial", 10)).pack(pady=10)
    tk.Label(settings_frame, text="Default Save Location:", bg="white", font=("Arial", 12)).pack(anchor="w", padx=20)
    location_frame = tk.Frame(settings_frame, bg="white")
    location_frame.pack(padx=20, pady=10, fill=tk.X)
    default_save_location_entry = tk.Entry(location_frame, width=30, font=("Arial", 10))
    default_save_location_entry.grid(row=0, column=0, sticky=tk.W)
    browse_button = tk.Button(location_frame, text="Browse", command=lambda: select_copy_to_dir(default_save_location_entry), bg="#70b966", fg="white", relief=tk.RAISED, font=("Arial", 10))
    browse_button.grid(row=0, column=1, padx=10)

    tk.Button(settings_frame, text="Save", command=save_settings_and_close, bg="#70b966", fg="white", relief=tk.RAISED, font=("Arial", 10)).pack(pady=20)

    load_current_settings()

def create_entry_with_label(frame, label_text, show_text=''):
    label = tk.Label(frame, text=label_text, bg="white", font=("Arial", 12))
    label.pack(anchor="w", padx=20)
    entry = tk.Entry(frame, width=30, font=("Arial", 10), show=show_text)
    entry.pack(padx=20, pady=5)
    return entry

def create_media_player_ui(window, vlc_player, media_length_in_seconds):
    print("[DEBUG] Entered create_media_player_ui with media_length (seconds):", media_length_in_seconds)

    media_length_ms = int(media_length_in_seconds * 1000)
    print("[DEBUG] Media length (in milliseconds):", media_length_ms)

    window.configure(bg='white') 
    player_frame = tk.Frame(window, bg='white')
    player_frame.pack()

   
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    play_icon_path = os.path.join(base_path, 'images', 'playicon32.png')
    pause_icon_path = os.path.join(base_path, 'images', 'pauseicon.png')
    stop_icon_path = os.path.join(base_path, 'images', 'stopicon.png')

  
    play_icon = ImageTk.PhotoImage(Image.open(play_icon_path))
    pause_icon = ImageTk.PhotoImage(Image.open(pause_icon_path))
    stop_icon = ImageTk.PhotoImage(Image.open(stop_icon_path))

    play_button = tk.Button(player_frame, image=play_icon, command=lambda: vlc_player.play(), bg='white')
    play_button.image = play_icon 
    play_button.pack(side="left")

    pause_button = tk.Button(player_frame, image=pause_icon, command=lambda: vlc_player.pause(), bg='white')
    pause_button.image = pause_icon 
    pause_button.pack(side="left")

    stop_button = tk.Button(player_frame, image=stop_icon, command=lambda: vlc_player.stop(), bg='white')
    stop_button.image = stop_icon 
    stop_button.pack(side="left")

    slider_frame = tk.Frame(window, bg='white')
    slider_frame.pack(fill='x', padx=10, pady=10)

    current_time_label = tk.Label(slider_frame, text="0:00", bg='white')
    current_time_label.pack(side="left")

    user_is_interacting = [False]

    def on_slider_start(event):
        user_is_interacting[0] = True

    def on_slider_end(event):
        user_is_interacting[0] = False
        if vlc_player.is_seekable():
            new_time_ms = int(float(seek_slider.get()) * 1000)
            vlc_player.set_time(new_time_ms)
            update_time_display(new_time_ms)  
            update_slider_position()  

    seek_slider = tk.Scale(slider_frame, from_=0, to=media_length_in_seconds, orient=tk.HORIZONTAL,
                           length=400, sliderrelief=tk.FLAT, sliderlength=20, troughcolor='gray',
                           bd=0, highlightthickness=0, bg='white', showvalue=0)
    seek_slider.pack(fill='x', expand=True)
    seek_slider.bind("<ButtonPress-1>", on_slider_start)  
    seek_slider.bind("<ButtonRelease-1>", on_slider_end)  

    def close_window():
        print("[DEBUG] Close button pressed.")
        if vlc_player.is_playing():
            print("[DEBUG] Stopping VLC player.")
            vlc_player.stop()
        window.destroy()
    
    window.protocol("WM_DELETE_WINDOW", close_window)

    def update_time_display(current_time_ms):
        remaining_time_ms = media_length_ms - current_time_ms
        minutes_remaining = remaining_time_ms // 60000
        seconds_remaining = (remaining_time_ms // 1000) % 60
        current_time_label.config(text=f"{minutes_remaining}:{seconds_remaining:02d} remaining")

    def update_slider_position():
        try:
            position_ms = vlc_player.get_time() 
            if position_ms == -1:  
                position_ms = 0

            if not user_is_interacting[0]:  
                if vlc_player.get_state() in [vlc.State.Playing, vlc.State.Paused, vlc.State.Stopped]:
                    seek_slider.set(position_ms // 1000)  

            update_time_display(position_ms)  

            if position_ms < media_length_ms or vlc_player.get_state() == vlc.State.Paused:
                window.after(50, update_slider_position)  
            else:
                print("[DEBUG] Media ended. Resetting player.")
                vlc_player.stop()  
                seek_slider.set(0)  
                current_time_label.config(text="0:00 remaining")  
        except Exception as e:
            print("[DEBUG] Error updating slider position:", e)

    update_slider_position() 

def on_call_select(tree, parent_window):
    selected_item = tree.item(tree.selection())['values']
    if not selected_item:
        return

    print(f"[DEBUG] Selected item in on_call_select: {selected_item}")

    action_window = tk.Toplevel(parent_window)
    action_window.title("Select Action")
    action_window.geometry("300x100")

    tk.Button(action_window, text="Play Call", command=lambda: play_audio(selected_item)).pack(pady=10)
    tk.Button(action_window, text="Download Call", command=lambda: download_selected_call(selected_item)).pack(pady=10)

import re

def download_selected_call(selected_item):
    filename = selected_item[1]
    date_modified = selected_item[2]
    directory_path = selected_item[0]
    wasabi_path = f"{directory_path}/{filename}"

    print(f"[DEBUG] Filename: {filename}")
    print(f"[DEBUG] Wasabi Path: {wasabi_path}")

    default_save_location = settings.get("DefaultSaveLocation", "")
    if not default_save_location:
        print("Default save location is not set.")
        return

    wasabi_client = create_wasabi_client()
    
    local_path = os.path.join(default_save_location, filename)

    try:
        with open(local_path, 'wb') as file:
            wasabi_client.download_fileobj(settings["S3"]["BucketName"], wasabi_path, file)
        print(f"Downloaded: {filename} to {local_path}")

        phone_number, agent_name, call_time = parse_filename(filename)
        formatted_date = format_date(date_modified)
        new_filename = f"{phone_number}_{agent_name.replace(' ', '_')}_{formatted_date}_{call_time.replace(':', '_').replace(' ', '_')}.wav"
        new_filename = re.sub(r'[\\/:*?"<>|]', '_', new_filename)
        new_local_path = os.path.join(default_save_location, new_filename)

        os.rename(local_path, new_local_path)
        print(f"Renamed to: {new_filename}")

    except Exception as e:
        print(f"Error downloading file from Wasabi: {str(e)}")


def test_sql_connection():
    sql_server = server_entry.get()
    sql_database = database_entry.get()

    test_connection_string = f"""
    Driver={{{settings["SQL"]["Driver"]}}};
    Server={sql_server};
    Database={sql_database};
    Trusted_Connection={{{settings["SQL"]["Trusted_Connection"]}}};
    """
    
    try:
        test_conn = pyodbc.connect(test_connection_string)
        test_conn.close()
        messagebox.showinfo("Test Connection", "SQL Connection Succeeded!")
    except Exception as e:
        print(f"Exception encountered: {e}")
        messagebox.showerror("Test Connection Failed", f"SQL Connection Failed!\nError: {str(e)}")

def extract_name_from_filename(filename):
    by_name_match = re.search(r'by ([^@]+)@', filename)
    if by_name_match:
        return by_name_match.group(1).replace('.', '_')
    
    underscore_name_match = re.match(r'([a-zA-Z]+)_', filename)
    if underscore_name_match:
        return underscore_name_match.group(1)

    return ""

def is_valid_phone_number(phone_number):
    return re.match(r'^(?![0|44|\+44]).{10}$', phone_number) is not None

def is_valid_date(date_text):
    try:
        datetime.strptime(date_text, '%d/%m/%Y')
        return True
    except ValueError:
        return False

def submit():
    save_directory = selected_directory.get()
    if not save_directory:
        messagebox.showerror("Error", "Please select a save directory first.")
        return

    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        cursor = conn.cursor()

        all_results = []
        validation_errors = []
        skip_count = 0

        for i in range(5):
            phone_number = phone_vars[i].get().strip()
            start_date = start_date_vars[i].get().strip()
            end_date = end_date_vars[i].get().strip()

            if (phone_number == "Phone Number" and start_date == "Start Date" and end_date == "End Date"):
                skip_count += 1
                continue
            if phone_number != "Phone Number" and not is_valid_phone_number(phone_number):
                validation_errors.append(f"Set {i + 1}: Invalid phone number format.")
                continue
            if start_date != "Start Date" and not is_valid_date(start_date):
                validation_errors.append(f"Set {i + 1}: Invalid start date format.")
                continue
            if end_date != "End Date" and not is_valid_date(end_date):
                validation_errors.append(f"Set {i + 1}: Invalid end date format.")
                continue

            cursor.execute("EXEC f9calltestSO @PhoneNumber=?, @StartDate=?, @EndDate=?", phone_number, start_date, end_date)
            results = cursor.fetchall()

            if results:
                for result in results:
                    all_results.append(result)
            else:
                print(f"No results found for set {i + 1}.")

        if skip_count == 5:
            messagebox.showinfo("Input Error", "Please input at least one search term.")
            return

        if validation_errors:
            messagebox.showerror("Validation Error", "\n".join(validation_errors))
            return

        if all_results:
            display_search_results(all_results)
        else:
            messagebox.showinfo("No Results", "No results found for the given search criteria.")

        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to search: {str(e)}")



def parse_filename(filename):
    phone_number, agent_email, call_time = "Unknown", "Unknown", "Unknown"

    phone_match = re.match(r'\+(\d+) ', filename)
    if phone_match:
        phone_number = phone_match.group(1)

    agent_match = re.search(r'by ([^@]+)@', filename)
    if agent_match:
        agent_email = agent_match.group(1)
        agent_name = agent_email.split('@')[0].replace('.', ' ')

    time_match = re.search(r'@ (.+).wav', filename)
    if time_match:
        call_time = time_match.group(1).replace('_', ':')
    
    return phone_number, agent_name, call_time


def format_date(date_obj):
    if isinstance(date_obj, datetime):
        return date_obj.strftime('%d/%m/%Y')
    elif isinstance(date_obj, date): 
        return date_obj.strftime('%d/%m/%Y')
    else:
        try:
            parsed_date = datetime.strptime(str(date_obj), '%Y-%m-%d %H:%M:%S.%f')
            return parsed_date.strftime('%d/%m/%Y')
        except (ValueError, TypeError) as e:
            print("Error parsing date:", e) 
            return "Unknown Date"

def display_search_results(results):
    results_window = tk.Toplevel(root)
    results_window.title("Search Results")
    results_window.configure(bg="white")
    results_window.geometry("700x700")

    num_results_per_page = 20
    total_pages = len(results) // num_results_per_page + (1 if len(results) % num_results_per_page > 0 else 0)
    current_page = [1]

    page_jump_combobox = None

    results.sort(key=lambda x: (x[2], parse_filename(x[1])[2]), reverse=True)

    def display_page(page_number):
        nonlocal page_jump_combobox
        for widget in results_window.winfo_children():
            widget.destroy()

        start_index = (page_number - 1) * num_results_per_page
        end_index = min(start_index + num_results_per_page, len(results))
        page_results = results[start_index:end_index]

        results_frame = tk.Frame(results_window, bg="white")
        results_frame.grid(row=0, column=0, sticky="nsew")

        headers = ["Phone", "Agent", "Time", "Duration", "Date", "Actions"]
        for col, header in enumerate(headers):
            tk.Label(results_frame, text=header, bg="white", font=("Arial", 10, "bold")).grid(row=0, column=col, padx=10, pady=2, sticky="w")

        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        play_icon_path = os.path.join(base_path, 'images', 'Playicon.png')
        download_icon_path = os.path.join(base_path, 'images', 'Downloadicon.png')
        play_icon_image = Image.open(play_icon_path)
        play_icon = ImageTk.PhotoImage(play_icon_image)
        download_icon_image = Image.open(download_icon_path)
        download_icon = ImageTk.PhotoImage(download_icon_image)

        for idx, row in enumerate(page_results):
            directory_path, filename, date_modified, call_length = row
            phone_number, agent_name, call_time = parse_filename(filename)

            print("Date before formatting:", date_modified)
            
            readable_duration = str(timedelta(seconds=call_length))
            formatted_date = format_date(date_modified)

            tk.Label(results_frame, text=phone_number, bg="white").grid(row=idx+1, column=0, padx=10, sticky="w")
            tk.Label(results_frame, text=agent_name, bg="white").grid(row=idx+1, column=1, padx=10, sticky="w")
            tk.Label(results_frame, text=call_time, bg="white").grid(row=idx+1, column=2, padx=10, sticky="w")
            tk.Label(results_frame, text=readable_duration, bg="white").grid(row=idx+1, column=3, padx=10, sticky="w")
            tk.Label(results_frame, text=formatted_date, bg="white").grid(row=idx+1, column=4, padx=10, sticky="w")

            action_frame = tk.Frame(results_frame, bg="white")
            action_frame.grid(row=idx+1, column=5, sticky="w")
    
            play_button = tk.Button(action_frame, image=play_icon, command=lambda f=row: play_audio(f, f[3]))

            play_button.image = play_icon 
            play_button.pack(side='left', padx=5)

            download_button = tk.Button(action_frame, image=download_icon,
                            command=lambda f=row: download_selected_call(f))
            download_button.image = download_icon 
            download_button.pack(side='left', padx=5)


        create_navigation_frame()
        create_page_jump_frame()

    def create_navigation_frame():
        nav_frame = tk.Frame(results_window, bg="white")
        nav_frame.grid(row=1, column=0, sticky="ew")

        if current_page[0] > 1:
            tk.Button(nav_frame, text="Previous Page", command=lambda: change_page(-1)).pack(side="left", padx=10)

        page_label = tk.Label(nav_frame, text=f"Page {current_page[0]} of {total_pages}", bg="white")
        page_label.pack(side="left", padx=10)

        if current_page[0] < total_pages:
            tk.Button(nav_frame, text="Next Page", command=lambda: change_page(1)).pack(side="left", padx=10)

    def create_page_jump_frame():
        nonlocal page_jump_combobox
        page_jump_frame = tk.Frame(results_window, bg="white")
        page_jump_frame.grid(row=2, column=0, sticky="ew", pady=10)

        page_jump_label = tk.Label(page_jump_frame, text="Jump to Page:", bg="white")
        page_jump_label.pack(side="left", padx=10)

        page_numbers = [str(i) for i in range(1, total_pages + 1)]
        page_jump_combobox = ttk.Combobox(page_jump_frame, values=page_numbers, width=10)
        page_jump_combobox.pack(side="left", padx=10)
        page_jump_combobox.bind("<<ComboboxSelected>>", jump_to_page)

    def jump_to_page(event):
        nonlocal page_jump_combobox
        page = page_jump_combobox.current() + 1
        display_page(page)

    def change_page(delta):
        current_page[0] += delta
        display_page(current_page[0])

    display_page(current_page[0])
      

def play_audio(selected_item, call_length):
    global vlc_player
    filename = selected_item[1]
    directory_path = selected_item[0]
    wasabi_path = f"{directory_path}/{filename}"
    local_temp_path = tempfile.mktemp(suffix='.wav') 

    print(f"[DEBUG] Playing audio from Wasabi Path: {wasabi_path}")

    wasabi_client = create_wasabi_client()
    try:
        with open(local_temp_path, 'wb') as file:
            wasabi_client.download_fileobj(settings["S3"]["BucketName"], wasabi_path, file)

        vlc_player = vlc.MediaPlayer(local_temp_path)
        vlc_player.play()

        media_controls_window = tk.Toplevel(root)
        media_controls_window.title("Media Player")
        media_controls_window.geometry("300x100")
        create_media_player_ui(media_controls_window, vlc_player, call_length)
    except Exception as e:
        print(f"Error in play_audio: {str(e)}")

def reset_inputs():
    for i in range(5):
        phone_vars[i].set(placeholders[0])
        first_name_vars[i].set(placeholders[1])
        last_name_vars[i].set(placeholders[2])
        start_date_vars[i].set(placeholders[3])
        end_date_vars[i].set(placeholders[4])

def clear_placeholder(event):
    current_value = event.widget.get()
    if current_value == event.widget.placeholder:
        event.widget.delete(0, tk.END)
        event.widget.config(fg="black")

def restore_placeholder(event):
    current_value = event.widget.get()
    if not current_value:
        event.widget.insert(0, event.widget.placeholder)
        if event.widget.placeholder == "Select Save Location":
            event.widget.config(fg="gray")  
        else:
            event.widget.config(fg="black")

def duplicate_start_date():
    value_to_copy = start_date_vars[0].get()
    for start_date_var in start_date_vars[1:]:
        start_date_var.set(value_to_copy)

def duplicate_end_date():
    value_to_copy = end_date_vars[0].get()
    for end_date_var in end_date_vars[1:]:
        end_date_var.set(value_to_copy)

base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
icon_path = os.path.join(base_path, 'Images', 'recordingsearch.ico')

root = tk.Tk()
root.title("Call Recording Search")
try:
    root.iconbitmap(default=icon_path)
except Exception as e:
    print(f"Error setting icon: {e}")

root.configure(bg="white")

banner = tk.Label(root, text="Call Recording Search", bg="#70b966", font=("Arial", 20), fg="white")
banner.pack(fill=tk.X, pady=20)

frame = tk.Frame(root, bg="white", padx=20, pady=1)
frame.pack()

global config_image_path, config_image_tk 

base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
select_dir_image_path = os.path.join(base_path, 'images', 'folder24.png')
select_dir_image_pil = Image.open(select_dir_image_path)
select_dir_image = ImageTk.PhotoImage(select_dir_image_pil)


selected_directory = tk.StringVar()
copy_to_dir_entry = tk.Entry(frame, width=36, bg="white", relief=tk.SOLID, textvariable=selected_directory, font=("Arial", 10))
default_save_location = settings.get("DefaultSaveLocation", "Select Save Location")

copy_to_dir_entry.placeholder = default_save_location
copy_to_dir_entry.insert(0, copy_to_dir_entry.placeholder)
copy_to_dir_entry.config(fg="gray")  

if default_save_location == "Select Save Location":
    copy_to_dir_entry.config(fg="gray")

copy_to_dir_entry.bind("<FocusIn>", clear_placeholder)
copy_to_dir_entry.bind("<FocusOut>", restore_placeholder)

copy_to_dir_button = tk.Button(frame, image=select_dir_image, command=lambda: select_copy_to_dir(copy_to_dir_entry), bg="white", relief=tk.FLAT)
copy_to_dir_button['relief'] = tk.RAISED
copy_to_dir_button['borderwidth'] = 2
copy_to_dir_tooltip = ToolTip(copy_to_dir_button, "Select the location you want to save the call recordings to.")

def on_enter(e):
    copy_to_dir_button['background'] = '#b0c4de'  

def on_leave(e):
    copy_to_dir_button['background'] = 'white'    

copy_to_dir_button.bind("<Enter>", on_enter)
copy_to_dir_button.bind("<Leave>", on_leave)

reset_button = tk.Button(frame, text="Reset Inputs", command=reset_inputs, bg="#70b966", fg="white", relief=tk.RAISED, font=("Arial", 12))
reset_button.grid(row=2, column=2, columnspan=3, pady=20)

copy_to_dir_entry.grid(row=1, column=1, columnspan=2, pady=5, padx=10, sticky="w")  
copy_to_dir_button.grid(row=1, column=2, pady=6, padx=10, sticky="w")  

num_entries = 5
phone_vars = [tk.StringVar() for _ in range(num_entries)]
first_name_vars = [tk.StringVar() for _ in range(num_entries)]
last_name_vars = [tk.StringVar() for _ in range(num_entries)]
start_date_vars = [tk.StringVar() for _ in range(num_entries)]
end_date_vars = [tk.StringVar() for _ in range(num_entries)]

phone_frame = tk.Frame(frame, bg="white")
phone_frame.grid(row=0, column=0, columnspan=3, pady=10)

placeholders = ["Phone Number", "First Name", "Last Name", "Start Date", "End Date"]

for i in range(num_entries):
    phone_entry = tk.Entry(phone_frame, width=20, bg="white", relief=tk.SOLID, font=("Arial", 10), textvariable=phone_vars[i])
    phone_entry.placeholder = placeholders[0]
    phone_entry.insert(0, phone_entry.placeholder)
    phone_entry.grid(row=i, column=0, padx=10, pady=5)
    phone_entry.bind("<FocusIn>", clear_placeholder)
    phone_entry.bind("<FocusOut>", restore_placeholder)
    phone_tooltip = ToolTip(phone_entry, "Please leave out +44, 44, and 0.")

    first_name_entry = tk.Entry(phone_frame, width=20, bg="white", relief=tk.SOLID, font=("Arial", 10), textvariable=first_name_vars[i])
    first_name_entry.placeholder = placeholders[1]
    first_name_entry.insert(0, first_name_entry.placeholder)
    first_name_entry.grid(row=i, column=1, padx=10, pady=5)
    first_name_entry.bind("<FocusIn>", clear_placeholder)
    first_name_entry.bind("<FocusOut>", restore_placeholder)
    first_name_tooltip = ToolTip(first_name_entry, "Ensure there are no spaces.")

    last_name_entry = tk.Entry(phone_frame, width=20, bg="white", relief=tk.SOLID, font=("Arial", 10), textvariable=last_name_vars[i])
    last_name_entry.placeholder = placeholders[2]
    last_name_entry.insert(0, last_name_entry.placeholder)
    last_name_entry.grid(row=i, column=2, padx=10, pady=5)
    last_name_entry.bind("<FocusIn>", clear_placeholder)
    last_name_entry.bind("<FocusOut>", restore_placeholder)
    last_name_tooltip = ToolTip(last_name_entry, "Ensure there are no spaces.")

    start_date_entry = tk.Entry(phone_frame, width=20, bg="white", relief=tk.SOLID, font=("Arial", 10), textvariable=start_date_vars[i])
    start_date_entry.placeholder = placeholders[3]
    start_date_entry.insert(0, start_date_entry.placeholder)
    start_date_entry.grid(row=i, column=3, padx=10, pady=5)
    start_date_entry.bind("<FocusIn>", clear_placeholder)
    start_date_entry.bind("<FocusOut>", restore_placeholder)
    start_date_tooltip = ToolTip(start_date_entry, "date format should be DD/MM/YYYY.")
    duplicate_start_date_button = tk.Button(phone_frame, text="Duplicate start date", command=duplicate_start_date, bg="#70b966", fg="white", relief=tk.RAISED, font=("Arial", 10))
    duplicate_start_date_button.grid(row=num_entries, column=3, padx=10, pady=10) 


    end_date_entry = tk.Entry(phone_frame, width=20, bg="white", relief=tk.SOLID, font=("Arial", 10), textvariable=end_date_vars[i])
    end_date_entry.placeholder = placeholders[4]
    end_date_entry.insert(0, end_date_entry.placeholder)
    end_date_entry.grid(row=i, column=4, padx=10, pady=5)
    end_date_entry.bind("<FocusIn>", clear_placeholder)
    end_date_entry.bind("<FocusOut>", restore_placeholder)
    end_date_tooltip = ToolTip(end_date_entry, "date format should be DD/MM/YYYY.")
    duplicate_end_date_button = tk.Button(phone_frame, text="Duplicate end date", command=duplicate_end_date, bg="#70b966", fg="white", relief=tk.RAISED, font=("Arial", 10))
    duplicate_end_date_button.grid(row=num_entries, column=4, padx=10, pady=10) 

submit_button = tk.Button(frame, text="Submit", command=submit, bg="#70b966", fg="white", relief=tk.RAISED, font=("Arial", 12))
submit_button.grid(row=2, column=0, columnspan=3, pady=20)

base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
config_image_path = os.path.join(base_path, 'images', 'settings32.png')
config_image_pil = Image.open(config_image_path)
config_image = ImageTk.PhotoImage(config_image_pil)
settings_button = tk.Button(frame, image=config_image, command=open_settings_window, bg="white", relief=tk.FLAT)
settings_button.grid(row=3, column=6, pady=10)
settings_button['relief'] = tk.RAISED
settings_button['borderwidth'] = 2
Settings_tooltip = ToolTip(settings_button, "Configuration for the application.")

def on_enter_settings(e):
    settings_button['background'] = '#b0c4de'

def on_leave_settings(e):
    settings_button['background'] = 'white'

settings_button.bind("<Enter>", on_enter_settings)
settings_button.bind("<Leave>", on_leave_settings)

root.mainloop()
