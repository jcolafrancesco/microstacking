# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Copyright 2024 Julien Colafrancesco
#

import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
from PIL import Image, ImageTk
import os
import serial
import gphoto2 as gp
import subprocess
import io
import time

arduino = None  # Variable to store the serial connection
camera_preview_active = False  # Variable to track camera preview state
subprocess.call(["gio", "mount", "-s", "gphoto2"])
subprocess.call(["mkdir", "-p", "Capture"])

camera_connected = False  # Variable to track camera connection state

try:
    camera = gp.check_result(gp.gp_camera_new())
    gp.check_result(gp.gp_camera_init(camera))
    config = gp.check_result(gp.gp_camera_get_config(camera))
    gp.gp_camera_capture_preview(camera)
    camera_connected = True
except gp.GPhoto2Error as e:
    print(f"Failed to initialize camera: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

def setup_window():
    window = ThemedTk(theme="arc")
    window.title("Microfocus stacker")
    window.geometry("1600x900")  # Increased window size
    return window

def setup_main_frame(window):
    main_frame = ttk.Frame(window, padding="20", width=300)
    main_frame.pack(side=tk.LEFT, fill=tk.Y)
    return main_frame

def setup_camera_frame(main_frame):
    camera_frame = ttk.LabelFrame(main_frame, text="Camera", padding="10")
    camera_frame.pack(pady=10, fill=tk.BOTH, expand=True)
    return camera_frame

def setup_image_frame(window):
    image_frame = ttk.Frame(window, padding="10", style="Black.TFrame")
    image_frame.pack(side=tk.TOP, padx=10, pady=10, expand=True, fill=tk.BOTH)
    return image_frame

def setup_full_image_canvas(image_frame):
    full_image_canvas = tk.Canvas(image_frame, background="black", bd=0, highlightthickness=0)
    full_image_canvas.pack(expand=True, fill=tk.BOTH)
    streaming_image = full_image_canvas.create_image(0, 0, anchor="center", image=None)
    full_image_canvas.photo = None  # Keep a reference to the PhotoImage object
    return full_image_canvas, streaming_image

def setup_strip_frame(window):
    strip_frame = ttk.Frame(window, padding="10")
    strip_frame.pack(side=tk.BOTTOM, fill=tk.X)
    return strip_frame

def setup_treeview(strip_frame):
    treeview = ttk.Treeview(strip_frame, columns=("Image"), show="tree", selectmode='browse')
    treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(strip_frame, orient=tk.VERTICAL, command=treeview.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    treeview.configure(yscrollcommand=scrollbar.set)
    treeview.image_dict = {}
    return treeview

def setup_controls(main_frame):
    connection_frame = setup_connection_frame(main_frame)
    manual_controls_frame = setup_manual_controls_frame(main_frame)
    stacking_frame = setup_stacking_frame(main_frame)
    return connection_frame, manual_controls_frame, stacking_frame

def setup_connection_frame(main_frame):
    connection_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
    connection_frame.pack(pady=10, fill=tk.BOTH, expand=True)
    return connection_frame

def setup_manual_controls_frame(main_frame):
    manual_controls_frame = ttk.LabelFrame(main_frame, text="Manual Controls", padding="10")
    manual_controls_frame.pack(pady=10, fill=tk.BOTH, expand=True)
    return manual_controls_frame

def setup_stacking_frame(main_frame):
    stacking_frame = ttk.LabelFrame(main_frame, text="Stacking", padding="10")
    stacking_frame.pack(pady=10, fill=tk.BOTH, expand=True)
    return stacking_frame

def setup_style():
    style = ttk.Style()
    style.configure("Black.TFrame", background="black")
    style.configure("TLabel", background=style.lookup("TFrame", "background"))
    style.configure("Green.TButton", foreground="green")

def create_label(frame, text, row, column, width=17, anchor=tk.E, pady=5, sticky=tk.W):
    label = ttk.Label(frame, text=text, width=width, anchor=anchor)
    label.grid(row=row, column=column, pady=pady, sticky=sticky)
    return label

def create_combobox(frame, values, row, column, width=10, default_value=None, pady=5, sticky=tk.W):
    combobox = ttk.Combobox(frame, values=values, width=width)
    if default_value:
        combobox.set(default_value)
    combobox.grid(row=row, column=column, pady=pady, sticky=sticky)
    return combobox

def create_spinbox(frame, from_, to, row, column, increment=1, width=10, default_value=None, pady=5, sticky=tk.W):
    spinbox = ttk.Spinbox(frame, from_=from_, to=to, increment=increment, width=width)
    if default_value:
        spinbox.set(default_value)
    spinbox.grid(row=row, column=column, pady=pady, sticky=sticky)
    return spinbox

def main():
    window = setup_window()
    main_frame = setup_main_frame(window)
    camera_frame = setup_camera_frame(main_frame)
    image_frame = setup_image_frame(window)
    full_image_canvas, streaming_image = setup_full_image_canvas(image_frame)
    strip_frame = setup_strip_frame(window)
    treeview = setup_treeview(strip_frame)
    connection_frame, manual_controls_frame, stacking_frame = setup_controls(main_frame)
    setup_style()

    current_image_path = None
    last_selected_image_path = None
    resize_timer = None
    stack_folder = None
    stop_capture = False  # Initialize stop_capture

    def toggle_camera_preview():
        global camera_preview_active
        camera_preview_active = not camera_preview_active
        if camera_preview_active:
            camera_button.config(text="Stop Preview")
            print("Camera preview activated")
            update_camera_preview()
        else:
            camera_button.config(text="Start Preview")
            print("Camera preview deactivated")
            if last_selected_image_path:
                show_full_image(last_selected_image_path)

    def capture_and_process_image():
        file_path = capture_image()
        process_captured_image(file_path, "Singles")

    def capture_image():
        try:
            print("Capturing image")
            start_time = time.time()
            file_path = gp.check_result(gp.gp_camera_capture(camera, gp.GP_CAPTURE_IMAGE))
            end_time = time.time()
            print(f"Time taken to capture image: {end_time - start_time} seconds")
            return file_path
        except gp.GPhoto2Error as e:
            print(f"Failed to capture image: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def process_captured_image(file_path, folder):
        try:
            target_folder = os.path.join("Capture", folder)
            os.makedirs(target_folder, exist_ok=True)
            target = os.path.join(target_folder, file_path.name)
            camera_file = gp.check_result(gp.gp_camera_file_get(camera, file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL))
            gp.check_result(gp.gp_file_save(camera_file, target))
            print(f"Image saved to {target}")
            add_image_to_treeview(target)
            show_full_image(target)  # Display the last image captured
            select_image_in_treeview(target)  # Select the last image captured in the treeview
        except gp.GPhoto2Error as e:
            print(f"Failed to process captured image: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def add_image_to_treeview(image_path):
        image = Image.open(image_path)
        image.thumbnail((100, 100))
        parent_folder = os.path.basename(os.path.dirname(image_path))
        if parent_folder == "Capture":
            parent_folder = os.path.basename(os.path.dirname(os.path.dirname(image_path)))
        if parent_folder not in treeview.image_dict:
            parent_id = treeview.insert('', 'end', text=parent_folder, open=True)
            treeview.image_dict[parent_folder] = parent_id
        else:
            parent_id = treeview.image_dict[parent_folder]
        image_name = os.path.basename(image_path)
        new_item = treeview.insert(parent_id, 'end', text=image_name)
        treeview.selection_set(new_item)
        treeview.see(new_item)

    def select_image_in_treeview(image_path):
        if os.path.isfile(image_path):
            for item in treeview.get_children():
                for sub_item in treeview.get_children(item):
                    if treeview.item(sub_item, "text") == os.path.basename(image_path):
                        treeview.selection_set(sub_item)
                        treeview.see(sub_item)
                        break

    def show_full_image(image_path):
        nonlocal current_image_path, last_selected_image_path
        if not camera_preview_active and os.path.isfile(image_path):
            current_image_path = image_path
            last_selected_image_path = image_path
            image = Image.open(image_path)
            resize_and_display_image(image)

    def resize_and_display_image(image):
        # Calculate the new size while maintaining the aspect ratio
        frame_width = image_frame.winfo_width()
        frame_height = image_frame.winfo_height()

        if frame_width > 0 and frame_height > 0:
            image_ratio = image.width / image.height
            frame_ratio = frame_width / frame_height

            if frame_ratio > image_ratio:
                new_height = frame_height
                new_width = int(new_height * image_ratio)
            else:
                new_width = frame_width
                new_height = int(new_width / image_ratio)

            if new_width > 0 and new_height > 0:
                resized_image = image.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized_image)
                full_image_canvas.itemconfig(streaming_image, image=photo)
                full_image_canvas.coords(streaming_image, frame_width // 2, frame_height // 2)  # Center the image
                full_image_canvas.photo = photo  # Keep a reference to the PhotoImage object

    def schedule_final_resize():
        nonlocal resize_timer
        resize_timer = None
        if camera_preview_active:
            update_camera_preview()
        elif current_image_path:
            image = Image.open(current_image_path)
            resize_and_display_image(image)

    def update_camera_preview():
        if camera_preview_active:
            try:
                camera_file = gp.check_result(gp.gp_camera_capture_preview(camera))
                file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
                image = Image.open(io.BytesIO(file_data))
                resize_and_display_image(image)
            except gp.GPhoto2Error as e:
                if e.code == gp.GP_ERROR_IO:
                    print(f"Failed to capture preview: {e}")
                    window.after(200, update_camera_preview)  # Wait a bit before retrying
                else:
                    print(f"Failed to capture preview: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
            window.after(round(1000/30), update_camera_preview)  # Increase interval to 200ms
        else:
            if last_selected_image_path:
                show_full_image(last_selected_image_path)

    def capture_stack_step(frame_index, num_frames, pre_shot_delay, pre_focus_delay, angle):
        if stop_capture or frame_index >= num_frames:
            send_command_to_arduino("R")
            launch_button.config(style="TButton")
            return
        
        def capture_next_image():
            file_path = capture_image()
            window.after(round(pre_focus_delay) * 1000, rotate_knob)
            process_captured_image(file_path, stack_folder)

        def rotate_knob():
            send_command_to_arduino(f"U{angle}")
            rot_time = 2 * angle / 360  # Time to rotate the stage by the specified angle
            window.after(round(rot_time) * 1000, lambda: capture_stack_step(frame_index + 1, num_frames, pre_shot_delay, pre_focus_delay, angle))

        window.after(round(pre_shot_delay) * 1000, capture_next_image)

    def capture_stack():
        nonlocal stop_capture, stack_folder
        stop_capture = False
        num_frames = int(frames_spinbox.get())
        pre_shot_delay = int(pre_shot_delay_spinbox.get())
        pre_focus_delay = int(pre_focus_delay_spinbox.get())
        angle = int(angle_stacking_spinbox.get())
        stack_folder = f"Stack_{time.strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(stack_folder, exist_ok=True)
        send_command_to_arduino("A")
        launch_button.config(style="Green.TButton")
        capture_stack_step(0, num_frames, pre_shot_delay, pre_focus_delay, angle)

    def stop_capture_stack():
        nonlocal stop_capture
        stop_capture = True

    def on_treeview_select(event):
        selected_item = treeview.selection()[0]
        parent_item = treeview.parent(selected_item)
        parent_folder = treeview.item(parent_item, "text")
        image_name = treeview.item(selected_item, "text")
        image_path = os.path.join("Capture", parent_folder, image_name)
        show_full_image(image_path)

    def load_images_from_folder(folder):
        singles_id = None
        folder_dict = {}
        for root, _, files in os.walk(folder):
            parent_folder = os.path.basename(root)
            if parent_folder == "Capture":
                parent_folder = os.path.basename(os.path.dirname(root))
            if parent_folder not in folder_dict:
                folder_dict[parent_folder] = []
            for file in files:
                if os.path.isfile(os.path.join(root, file)) and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.cr2')):
                    image_path = os.path.join(root, file)
                    folder_dict[parent_folder].append(image_path)
        for parent_folder in sorted(folder_dict.keys()):
            if parent_folder:  # Ensure parent_folder is not empty
                parent_id = treeview.insert('', 'end', text=parent_folder, open=(parent_folder == "Singles"))
                treeview.image_dict[parent_folder] = parent_id
                if parent_folder == "Singles":
                    singles_id = parent_id
                for image_path in sorted(folder_dict[parent_folder]):
                    image_name = os.path.basename(image_path)
                    treeview.insert(parent_id, 'end', text=image_name)
        return singles_id

    def display_first_image():
        if singles_id and treeview.get_children(singles_id):
            first_image_path = treeview.item(treeview.get_children(singles_id)[0], "text")
            show_full_image(first_image_path)
            treeview.selection_set(treeview.get_children(singles_id)[0])
            treeview.see(treeview.get_children(singles_id)[0])
        elif treeview.get_children():
            first_image_path = treeview.item(treeview.get_children()[0], "text")
            show_full_image(first_image_path)
            select_image_in_treeview(first_image_path)

    def on_resize(event):
        nonlocal resize_timer
        if resize_timer is not None:
            window.after_cancel(resize_timer)
        
        resize_timer = window.after(50, schedule_final_resize)

    def send_command_to_arduino(command):
        global arduino
        if arduino:
            arduino.write(command.encode())
        else:
            print("Arduino not connected")

    def move_up():
        send_command_to_arduino("A")
        send_command_to_arduino(f"U{angle_spinbox.get()}")
        send_command_to_arduino("R")

    def move_down():
        send_command_to_arduino("A")
        send_command_to_arduino(f"D{angle_spinbox.get()}")
        send_command_to_arduino("R")

    def update_ttys():
        ttys = [f"/dev/{tty}" for tty in os.listdir('/dev') if tty.startswith('tty')]
        tty_combobox['values'] = ttys
        if ttys:
            tty_combobox.set(ttys[-1])  # Set to the last tty in the list

    def connect():
        global arduino
        tty = tty_combobox.get()
        baudrate = baudrate_combobox.get()
        try:
            arduino = serial.Serial(tty, baudrate)
            status_label.config(text="Status: Connected", foreground="green")
            up_button.config(state=tk.NORMAL)
            down_button.config(state=tk.NORMAL)
        except Exception as e:
            print(f"Failed to connect: {e}")
            status_label.config(text="Status: Unconnected", foreground="red")

    def populate_combobox(widget_name, combobox):
        try:
            OK, widget = gp.gp_widget_get_child_by_name(config, widget_name)
            if OK >= gp.GP_OK:
                values = [gp.gp_widget_get_choice(widget, i)[1] for i in range(gp.gp_widget_count_choices(widget))]
                combobox['values'] = values
                current_value = gp.gp_widget_get_value(widget)[1]
                combobox.set(current_value)
        except gp.GPhoto2Error as e:
            print(f"Failed to get {widget_name} values: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def set_camera_value(event, widget_name, combobox):
        try:
            OK, widget = gp.gp_widget_get_child_by_name(config, widget_name)
            if OK >= gp.GP_OK:
                widget.set_value(combobox.get())
                camera.set_config(config)
        except gp.GPhoto2Error as e:
            print(f"Failed to set {widget_name} value: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    # Add Shutter Speed control
    shutter_speed_label = create_label(camera_frame, "Shutter Speed: ", row=2, column=0)
    shutter_speed_combobox = create_combobox(camera_frame, values=[], row=2, column=1)

    # Add ISO control
    iso_label = create_label(camera_frame, "ISO: ", row=3, column=0)
    iso_combobox = create_combobox(camera_frame, values=[], row=3, column=1)

    # Add White Balance control
    white_balance_label = create_label(camera_frame, "White Balance: ", row=4, column=0)
    white_balance_combobox = create_combobox(camera_frame, values=[], row=4, column=1)

    # Add Image Format control
    image_format_label = create_label(camera_frame, "Image Format: ", row=5, column=0)
    image_format_combobox = create_combobox(camera_frame, values=[], row=5, column=1)

    iso_combobox.bind("<<ComboboxSelected>>", lambda event: set_camera_value(event, 'iso', iso_combobox))
    shutter_speed_combobox.bind("<<ComboboxSelected>>", lambda event: set_camera_value(event, 'shutterspeed', shutter_speed_combobox))
    white_balance_combobox.bind("<<ComboboxSelected>>", lambda event: set_camera_value(event, 'whitebalance', white_balance_combobox))
    image_format_combobox.bind("<<ComboboxSelected>>", lambda event: set_camera_value(event, 'imageformat', image_format_combobox))

    populate_combobox('iso', iso_combobox)
    populate_combobox('shutterspeed', shutter_speed_combobox)
    populate_combobox('whitebalance', white_balance_combobox)
    populate_combobox('imageformat', image_format_combobox)

    capture_button = ttk.Button(camera_frame, text="Capture", command=capture_and_process_image, width=15)
    capture_button.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    camera_button = ttk.Button(camera_frame, text="Start Preview", command=toggle_camera_preview, width=15)
    camera_button.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    update_button = ttk.Button(connection_frame, text="Update TTY", command=update_ttys)
    update_button.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    tty_label = create_label(connection_frame, "Select TTY: ", row=1, column=0)
    tty_combobox = create_combobox(connection_frame, values=[], row=1, column=1)

    baudrate_label = create_label(connection_frame, "Baudrate: ", row=2, column=0)
    baudrate_combobox = create_combobox(connection_frame, ["9600", "19200", "38400", "57600", "115200"], row=2, column=1, default_value="9600")

    connect_button = ttk.Button(connection_frame, text="Connect", command=connect)
    connect_button.grid(row=3, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    status_label = ttk.Label(connection_frame, text="Status: Unconnected", foreground="red", anchor=tk.E)
    status_label.grid(row=4, column=0, columnspan=2, pady=5)

    update_ttys()  # Update the list of TTYs at app initialization
    connect()  # Try to connect to the selected TTY after updating the list

    angle_label = create_label(manual_controls_frame, "Angle (degrees): ", row=0, column=0)
    angle_spinbox = create_spinbox(manual_controls_frame, from_=0, to=360, row=0, column=1, default_value=15)

    up_button = ttk.Button(manual_controls_frame, text="↑", command=move_up)
    up_button.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)
    up_button.config(state=tk.DISABLED)

    down_button = ttk.Button(manual_controls_frame, text="↓", command=move_down)
    down_button.grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)
    down_button.config(state=tk.DISABLED)

    frames_label = create_label(stacking_frame, "Number of Frames: ", row=0, column=0)
    frames_spinbox = create_spinbox(stacking_frame, from_=1, to=100, row=0, column=1, default_value=3)

    pre_shot_delay_label = create_label(stacking_frame, "Pre-Shot Delay: ", row=1, column=0)
    pre_shot_delay_spinbox = create_spinbox(stacking_frame, from_=0, to=60, row=1, column=1, default_value=1)

    pre_focus_delay_label = create_label(stacking_frame, "Pre-Focus Delay: ", row=2, column=0)
    pre_focus_delay_spinbox = create_spinbox(stacking_frame, from_=0, to=60, row=2, column=1, default_value=0)

    angle_stacking_label = create_label(stacking_frame, "Angle (degrees): ", row=3, column=0)
    angle_stacking_spinbox = create_spinbox(stacking_frame, from_=0, to=360, row=3, column=1, default_value=30)

    launch_button = ttk.Button(stacking_frame, text="Capture Stack", command=capture_stack, width=15)
    launch_button.grid(row=4, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    stop_button = ttk.Button(stacking_frame, text="Stop", command=stop_capture_stack, width=15)
    stop_button.grid(row=5, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    treeview.bind("<<TreeviewSelect>>", on_treeview_select)

    start_time = time.time()
    singles_id = load_images_from_folder("Capture")
    end_time = time.time()
    print(f"Time taken to load images: {end_time - start_time} seconds")

    window.after(100, display_first_image)  # Display the first image after the window is initialized

    window.bind("<Configure>", on_resize)  # Bind the resize event to update the image size

    if not camera_connected:
        camera_button.config(state=tk.DISABLED)
        capture_button.config(state=tk.DISABLED)
        shutter_speed_combobox.config(state=tk.DISABLED)
        iso_combobox.config(state=tk.DISABLED)
        white_balance_combobox.config(state=tk.DISABLED)
        image_format_combobox.config(state=tk.DISABLED)
        launch_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.DISABLED)
        print("Camera controls disabled due to no camera connection")

    window.mainloop()

if __name__ == "__main__":
    main()
