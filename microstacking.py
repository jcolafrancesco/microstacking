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
camera = gp.check_result(gp.gp_camera_new())
gp.check_result(gp.gp_camera_init(camera))
config = gp.check_result(gp.gp_camera_get_config(camera))
gp.gp_camera_capture_preview(camera)

def main():
    window = ThemedTk(theme="arc")
    window.title("Microfocus stacker")
    window.geometry("1600x900")  # Increased window size

    # Create a frame
    main_frame = ttk.Frame(window, padding="20", width=300)
    main_frame.pack(side=tk.LEFT, fill=tk.Y)

    # Camera section
    camera_frame = ttk.LabelFrame(main_frame, text="Camera", padding="10")
    camera_frame.pack(pady=10, fill=tk.BOTH, expand=True)

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
            if current_image_path:
                show_full_image(current_image_path)

    def capture_image():
        try:
            print("Capturing image")
            file_path = gp.check_result(gp.gp_camera_capture(camera, gp.GP_CAPTURE_IMAGE))
            target = os.path.join('Capture', file_path.name)
            camera_file = gp.check_result(gp.gp_camera_file_get(camera, file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL))
            gp.check_result(gp.gp_file_save(camera_file, target))
            print(f"Image saved to {target}")
            add_image_to_treeview(target)
            show_full_image(target)  # Display the last image captured
            select_image_in_treeview(target)  # Select the last image captured in the treeview
        except gp.GPhoto2Error as e:
            print(f"Failed to capture image: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def add_image_to_treeview(image_path):
        image = Image.open(image_path)
        image.thumbnail((100, 100))
        photo = ImageTk.PhotoImage(image)
        treeview.insert('', 'end', text=image_path)
        treeview.image_dict[image_path] = photo

    def select_image_in_treeview(image_path):
        for item in treeview.get_children():
            if treeview.item(item, "text") == image_path:
                treeview.selection_set(item)
                treeview.see(item)
                break

    capture_button = ttk.Button(camera_frame, text="Capture", command=capture_image, width=15)
    capture_button.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    camera_button = ttk.Button(camera_frame, text="Start Preview", command=toggle_camera_preview, width=15)
    camera_button.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    # Add Shutter Speed control
    shutter_speed_label = ttk.Label(camera_frame, text="Shutter Speed: ", width=17, anchor=tk.E)
    shutter_speed_label.grid(row=2, column=0, pady=5, sticky=tk.W)
    shutter_speed_combobox = ttk.Combobox(camera_frame, values=[], width=10)
    shutter_speed_combobox.grid(row=2, column=1, pady=5, sticky=tk.W)

    # Add ISO control
    iso_label = ttk.Label(camera_frame, text="ISO: ", width=17, anchor=tk.E)
    iso_label.grid(row=3, column=0, pady=5, sticky=tk.W)
    iso_combobox = ttk.Combobox(camera_frame, values=[], width=10)
    iso_combobox.grid(row=3, column=1, pady=5, sticky=tk.W)

    # Add White Balance control
    white_balance_label = ttk.Label(camera_frame, text="White Balance: ", width=17, anchor=tk.E)
    white_balance_label.grid(row=4, column=0, pady=5, sticky=tk.W)
    white_balance_combobox = ttk.Combobox(camera_frame, values=[], width=10)
    white_balance_combobox.grid(row=4, column=1, pady=5, sticky=tk.W)

    # Add Image Format control
    image_format_label = ttk.Label(camera_frame, text="Image Format: ", width=17, anchor=tk.E)
    image_format_label.grid(row=5, column=0, pady=5, sticky=tk.W)
    image_format_combobox = ttk.Combobox(camera_frame, values=[], width=10)
    image_format_combobox.grid(row=5, column=1, pady=5, sticky=tk.W)

    def populate_iso_combobox():
        try:
            OK, iso_widget = gp.gp_widget_get_child_by_name(config, 'iso')
            if OK >= gp.GP_OK:
                iso_values = [gp.gp_widget_get_choice(iso_widget, i)[1] for i in range(gp.gp_widget_count_choices(iso_widget))]
                iso_combobox['values'] = iso_values
                current_iso = gp.gp_widget_get_value(iso_widget)[1]
                iso_combobox.set(current_iso)
        except gp.GPhoto2Error as e:
            print(f"Failed to get ISO values: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def populate_shutter_speed_combobox():
        try:
            OK, shutter_speed_widget = gp.gp_widget_get_child_by_name(config, 'shutterspeed')
            if OK >= gp.GP_OK:
                shutter_speed_values = [gp.gp_widget_get_choice(shutter_speed_widget, i)[1] for i in range(gp.gp_widget_count_choices(shutter_speed_widget))]
                shutter_speed_combobox['values'] = shutter_speed_values
                current_shutter_speed = gp.gp_widget_get_value(shutter_speed_widget)[1]
                shutter_speed_combobox.set(current_shutter_speed)
        except gp.GPhoto2Error as e:
            print(f"Failed to get Shutter Speed values: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def populate_white_balance_combobox():
        try:
            OK, white_balance_widget = gp.gp_widget_get_child_by_name(config, 'whitebalance')
            if OK >= gp.GP_OK:
                white_balance_values = [gp.gp_widget_get_choice(white_balance_widget, i)[1] for i in range(gp.gp_widget_count_choices(white_balance_widget))]
                white_balance_combobox['values'] = white_balance_values
                current_white_balance = gp.gp_widget_get_value(white_balance_widget)[1]
                white_balance_combobox.set(current_white_balance)
        except gp.GPhoto2Error as e:
            print(f"Failed to get White Balance values: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def populate_image_format_combobox():
        try:
            OK, image_format_widget = gp.gp_widget_get_child_by_name(config, 'imageformat')
            if OK >= gp.GP_OK:
                image_format_values = [gp.gp_widget_get_choice(image_format_widget, i)[1] for i in range(gp.gp_widget_count_choices(image_format_widget))]
                image_format_combobox['values'] = image_format_values
                current_image_format = gp.gp_widget_get_value(image_format_widget)[1]
                image_format_combobox.set(current_image_format)
        except gp.GPhoto2Error as e:
            print(f"Failed to get Image Format values: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def set_iso_value(event):
        try:
            OK, iso_widget = gp.gp_widget_get_child_by_name(config, 'iso')
            if OK >= gp.GP_OK:
                print(iso_combobox.get())
                iso_widget.set_value(iso_combobox.get())
                camera.set_config(config)
        except gp.GPhoto2Error as e:
            print(f"Failed to set ISO value: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def set_shutter_speed_value(event):
        try:
            OK, shutter_speed_widget = gp.gp_widget_get_child_by_name(config, 'shutterspeed')
            if OK >= gp.GP_OK:
                shutter_speed_widget.set_value(shutter_speed_combobox.get())
                camera.set_config(config)
        except gp.GPhoto2Error as e:
            print(f"Failed to set Shutter Speed value: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def set_white_balance_value(event):
        try:
            OK, white_balance_widget = gp.gp_widget_get_child_by_name(config, 'whitebalance')
            if OK >= gp.GP_OK:
                white_balance_widget.set_value(white_balance_combobox.get())
                camera.set_config(config)
        except gp.GPhoto2Error as e:
            print(f"Failed to set White Balance value: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def set_image_format_value(event):
        try:
            OK, image_format_widget = gp.gp_widget_get_child_by_name(config, 'imageformat')
            if OK >= gp.GP_OK:
                image_format_widget.set_value(image_format_combobox.get())
                camera.set_config(config)
        except gp.GPhoto2Error as e:
            print(f"Failed to set Image Format value: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    iso_combobox.bind("<<ComboboxSelected>>", set_iso_value)
    shutter_speed_combobox.bind("<<ComboboxSelected>>", set_shutter_speed_value)
    white_balance_combobox.bind("<<ComboboxSelected>>", set_white_balance_value)
    image_format_combobox.bind("<<ComboboxSelected>>", set_image_format_value)

    populate_iso_combobox()
    populate_shutter_speed_combobox()
    populate_white_balance_combobox()
    populate_image_format_combobox()

    # Connection section
    connection_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
    connection_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    tty_combobox = ttk.Combobox(connection_frame, width=10)
    baudrate_combobox = ttk.Combobox(connection_frame, values=["9600", "19200", "38400", "57600", "115200"], width=10)
    baudrate_combobox.set("9600")  # Default value

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
        except Exception as e:
            print(f"Failed to connect: {e}")
            status_label.config(text="Status: Unconnected", foreground="red")

    update_button = ttk.Button(connection_frame, text="Update TTY", command=update_ttys)
    update_button.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    tty_label = ttk.Label(connection_frame, text="Select TTY: ", width=17, anchor=tk.E)
    tty_label.grid(row=1, column=0, pady=5, sticky=tk.W)
    tty_combobox.grid(row=1, column=1, pady=5, sticky=tk.W)

    baudrate_label = ttk.Label(connection_frame, text="Baudrate: ", width=17, anchor=tk.E)
    baudrate_label.grid(row=2, column=0, pady=5, sticky=tk.W)
    baudrate_combobox.grid(row=2, column=1, pady=5, sticky=tk.W)

    connect_button = ttk.Button(connection_frame, text="Connect", command=connect)
    connect_button.grid(row=3, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    status_label = ttk.Label(connection_frame, text="Status: Unconnected", foreground="red", anchor=tk.E)
    status_label.grid(row=4, column=0, columnspan=2, pady=5)

    update_ttys()  # Update the list of TTYs at app initialization
    connect()  # Try to connect to the selected TTY after updating the list

    # Manual Controls section
    manual_controls_frame = ttk.LabelFrame(main_frame, text="Manual Controls", padding="10")
    manual_controls_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    angle_label = ttk.Label(manual_controls_frame, text="Angle (degrees): ", width=17, anchor=tk.E)
    angle_label.grid(row=0, column=0, pady=5, sticky=tk.W)
    angle_spinbox = ttk.Spinbox(manual_controls_frame, from_=0, to=360, increment=1, width=10)
    angle_spinbox.set(15)  # Default value
    angle_spinbox.grid(row=0, column=1, pady=5, sticky=tk.W)

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

    up_button = ttk.Button(manual_controls_frame, text="↑", command=move_up)
    up_button.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    down_button = ttk.Button(manual_controls_frame, text="↓", command=move_down)
    down_button.grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    # Stacking section
    stacking_frame = ttk.LabelFrame(main_frame, text="Stacking", padding="10")
    stacking_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    frames_label = ttk.Label(stacking_frame, text="Number of Frames: ", width=17, anchor=tk.E)
    frames_label.grid(row=0, column=0, pady=5, sticky=tk.W)
    frames_spinbox = ttk.Spinbox(stacking_frame, from_=1, to=100, increment=1, width=10)
    frames_spinbox.set(3)  # Default value
    frames_spinbox.grid(row=0, column=1, pady=5, sticky=tk.W)

    pre_shot_delay_label = ttk.Label(stacking_frame, text="Pre-Shot Delay: ", width=17, anchor=tk.E)
    pre_shot_delay_label.grid(row=1, column=0, pady=5, sticky=tk.W)
    pre_shot_delay_spinbox = ttk.Spinbox(stacking_frame, from_=0, to=60, increment=1, width=10)
    pre_shot_delay_spinbox.set(2)  # Default value
    pre_shot_delay_spinbox.grid(row=1, column=1, pady=5, sticky=tk.W)

    pre_focus_delay_label = ttk.Label(stacking_frame, text="Pre-Focus Delay: ", width=17, anchor=tk.E)
    pre_focus_delay_label.grid(row=2, column=0, pady=5, sticky=tk.W)
    pre_focus_delay_spinbox = ttk.Spinbox(stacking_frame, from_=0, to=60, increment=1, width=10)
    pre_focus_delay_spinbox.set(2)  # Default value
    pre_focus_delay_spinbox.grid(row=2, column=1, pady=5, sticky=tk.W)

    angle_stacking_label = ttk.Label(stacking_frame, text="Angle (degrees): ", width=17, anchor=tk.E)
    angle_stacking_label.grid(row=3, column=0, pady=5, sticky=tk.W)
    angle_stacking_spinbox = ttk.Spinbox(stacking_frame, from_=0, to=360, increment=1, width=10)
    angle_stacking_spinbox.set(30)  # Default value
    angle_stacking_spinbox.grid(row=3, column=1, pady=5, sticky=tk.W)

    stop_capture = False

    def capture_stack_step(frame_index, num_frames, pre_shot_delay, pre_focus_delay, angle):
        if stop_capture or frame_index >= num_frames:
            send_command_to_arduino("R")
            launch_button.config(style="TButton")
            return
        rot_time = 2 * angle / 360  # Time to rotate the stage by the specified angle
        window.after(round(pre_shot_delay) * 1000, lambda: capture_image())
        window.after(round(pre_shot_delay + pre_focus_delay) * 1000, lambda: send_command_to_arduino(f"U{angle}"))
        window.after(round(pre_shot_delay + pre_focus_delay + rot_time) * 1000, lambda: capture_stack_step(frame_index + 1, num_frames, pre_shot_delay, pre_focus_delay, angle))

    def capture_stack():
        nonlocal stop_capture
        stop_capture = False
        num_frames = int(frames_spinbox.get())
        pre_shot_delay = int(pre_shot_delay_spinbox.get())
        pre_focus_delay = int(pre_focus_delay_spinbox.get())
        angle = int(angle_stacking_spinbox.get())
        send_command_to_arduino("A")
        launch_button.config(style="Green.TButton")
        capture_stack_step(0, num_frames, pre_shot_delay, pre_focus_delay, angle)

    def stop_capture_stack():
        nonlocal stop_capture
        stop_capture = True

    launch_button = ttk.Button(stacking_frame, text="Capture Stack", command=capture_stack, width=15)
    launch_button.grid(row=4, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    stop_button = ttk.Button(stacking_frame, text="Stop", command=stop_capture_stack, width=15)
    stop_button.grid(row=5, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)

    # Create a frame for the image strip
    strip_frame = ttk.Frame(window, padding="10")
    strip_frame.pack(side=tk.BOTTOM, fill=tk.X)

    treeview = ttk.Treeview(strip_frame, columns=("Image"), show="tree", selectmode='browse')
    treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(strip_frame, orient=tk.VERTICAL, command=treeview.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    treeview.configure(yscrollcommand=scrollbar.set)
    treeview.image_dict = {}

    def on_treeview_select(event):
        selected_item = treeview.selection()[0]
        image_path = treeview.item(selected_item, "text")
        show_full_image(image_path)

    treeview.bind("<<TreeviewSelect>>", on_treeview_select)

    # Create a frame for displaying the full image
    image_frame = ttk.Frame(window, padding="10", style="Black.TFrame")
    image_frame.pack(side=tk.RIGHT, padx=10, pady=10, expand=True, fill=tk.BOTH)

    # Create a label for displaying the full image
    full_image_label = ttk.Label(image_frame)
    full_image_label.pack(expand=True)

    current_image_path = None
    last_selected_image_path = None
    resize_timer = None

    def show_full_image(image_path):
        nonlocal current_image_path, last_selected_image_path
        if not camera_preview_active and image_path != current_image_path:
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

            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(resized_image)
            full_image_label.config(image=photo)
            full_image_label.image = photo
            full_image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)  # Center the image

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
                    window.after(100, update_camera_preview)  # Wait a bit before retrying
                else:
                    print(f"Failed to capture preview: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
            window.after(50, update_camera_preview)  # Schedule next update in 50ms (20 times per second)
        else:
            if last_selected_image_path:
                show_full_image(last_selected_image_path)

    # Load and display images from the specified folder
    image_folder = "Capture"
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.cr2'))]

    def display_first_image():
        if image_files:
            first_image_path = os.path.join(image_folder, image_files[0])
            show_full_image(first_image_path)

    for image_file in image_files:
        image_path = os.path.join(image_folder, image_file)
        treeview.insert('', 'end', text=image_path)

    window.after(100, display_first_image)  # Display the first image after the window is initialized

    def on_resize(event):
        nonlocal resize_timer
        if resize_timer is not None:
            window.after_cancel(resize_timer)
        
        resize_timer = window.after(50, schedule_final_resize)

    window.bind("<Configure>", on_resize)  # Bind the resize event to update the image size

    style = ttk.Style()
    style.configure("Black.TFrame", background="black")
    style.configure("TLabel", background=style.lookup("TFrame", "background"))
    style.configure("Green.TButton", foreground="green")

    window.mainloop()

if __name__ == "__main__":
    main()
