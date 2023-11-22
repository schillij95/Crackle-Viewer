import tkinter as tk
import tkinter.colorchooser
from tkinter import filedialog
import textwrap
from PIL import Image, ImageTk, ImageDraw, ImageChops, ImageEnhance
# No decompression bomb error
Image.MAX_IMAGE_PIXELS = None
import math
import numpy as np
import os
import sys
import glob

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.my_title = "Vesuvius Crackle Viewer"
        self.master.title(self.my_title)
        if getattr(sys, 'frozen', False):
            # Running as compiled
            base_path = sys._MEIPASS
        else:
            # Running as script
            base_path = os.path.dirname(__file__)
        icon_path = os.path.join(base_path, 'crackle_viewer.png')
        # Set the window icon
        icon = tk.PhotoImage(file=icon_path)   
        self.master.tk.call('wm', 'iconphoto', self.master._w, icon)
        self.master.geometry("800x600")
        self.master.minsize(width=800, height=600)
        self.load_last_directory()  # Load the last directory
        self.images_folder = ""
        self.pil_image = None
        self.sub_overlays = []
        self.sub_overlay_colors = ['white', 'green', 'red', 'blue', 'yellow', 'cyan', 'magenta']
        self.sub_overlay_names = ['overlay.png']
        self.current_sub_overlay = tk.StringVar() 
        self.current_sub_overlay.set("None") 
        self.current_sub_overlay.trace("w", self.suboverlay_selected)
        self.create_menu()
        self.create_widget()
        self.reset_transform()
        self.image_list = []
        self.image_index = 0
        self.cursor_circle = None
        self.shift_pressed = False
        self.mouse_is_pressed = False
        self.overlay_image = None
        self.overlay_visibility = tk.BooleanVar(value=True)
        self.pencil_color = 'white'
        self.pencil_size = 12
        self.create_overlay_controls()

    def menu_open_clicked(self, event=None):
        self.load_images()

    def menu_quit_clicked(self):
        self.master.destroy() 

    def create_menu(self):
        self.menu_bar = tk.Menu(self) 
 
        self.file_menu = tk.Menu(self.menu_bar, tearoff = tk.OFF)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.file_menu.add_command(label="Open", command = self.menu_open_clicked, accelerator="Ctrl+O")
        self.file_menu.add_separator() 
        self.file_menu.add_command(label="Exit", command = self.menu_quit_clicked)

        self.menu_bar.bind_all("<Control-o>", self.menu_open_clicked)

        self.help_menu = tk.Menu(self.menu_bar, tearoff=tk.OFF)
        self.menu_bar.add_command(label="Help", command=self.show_help)

        self.master.config(menu=self.menu_bar)

    def create_overlay_controls(self):
        self.overlay_frame = tk.Frame(self.master)
        self.overlay_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.overlay_btn = tk.Button(self.overlay_frame, text="Load Overlay", command=self.load_overlay_image)
        self.overlay_btn.pack(side=tk.LEFT)

        self.create_empty_image_btn = tk.Button(self.overlay_frame, text="Create Empty Image", command=self.create_empty_overlay_image)
        self.create_empty_image_btn.pack(side=tk.LEFT, padx=5)


        self.save_btn = tk.Button(self.overlay_frame, text="Save Overlay", command=self.save_overlay)
        self.save_btn.pack(side=tk.LEFT)

        self.save_combined_btn = tk.Button(self.overlay_frame, text="Save Combined Overlays", command=self.save_combined_overlays)
        self.save_combined_btn.pack(side=tk.LEFT)
        
        self.overlay_check = tk.Checkbutton(self.overlay_frame, text="Show Overlay", variable=self.overlay_visibility, command=self.toggle_overlay)
        self.overlay_check.pack(side=tk.LEFT)
        
        self.color_btn = tk.Button(self.overlay_frame, text="Toggle Color", command=self.toggle_color)
        self.color_btn.pack(side=tk.LEFT)

        self.color_label = tk.Label(self.overlay_frame, text="", width=5, background=self.pencil_color)
        self.color_label.pack(side=tk.LEFT, padx=5)
        self.color_label.bind("<Button-1>", lambda e: self.toggle_color()) # Add this line in create_overlay_controls method

        # Add slider for overlay opacity control
        self.overlay_opacity_scale = tk.Scale(self.overlay_frame, from_=0, to_=255, orient=tk.HORIZONTAL, label="Overlay Opacity")
        self.overlay_opacity_scale.bind("<Motion>", self.adjust_overlay_opacity) # Bind the slider's motion to adjust opacity
        self.overlay_opacity_scale.pack(side=tk.LEFT)
        self.overlay_opacity_scale.config(from_=0, to=1, resolution=0.01)
        self.overlay_opacity_scale.set(1.0)

        # Entry to set opacity value manually
        self.overlay_opacity_entry = tk.Entry(self.overlay_frame, width=5)
        self.overlay_opacity_entry.pack(side=tk.LEFT, padx=5)
        self.overlay_opacity_entry.insert(tk.END, '1.0')
        self.overlay_opacity_entry.bind('<Return>', self.set_opacity_from_entry)

        self.pick_color_btn = tk.Button(self.overlay_frame, text="Pick Color", command=self.pick_color)
        self.pick_color_btn.pack(side=tk.LEFT)
        
        self.size_scale = tk.Scale(self.overlay_frame, from_=1, to_=200, orient=tk.HORIZONTAL, label="Pencil Size")
        self.size_scale.set(self.pencil_size)
        self.size_scale.pack(side=tk.LEFT)

        self.suboverlay_frame = tk.Frame(self.master)  # Create a new frame for SubOverlay-related controls
        self.suboverlay_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)  # Pack it below the existing frame

        # Dropdown to select a sub-overlay
        self.suboverlay_label = tk.Label(self.suboverlay_frame, text="Select Overlay:")
        self.suboverlay_label.pack(side=tk.LEFT)

        self.select_suboverlay_optionmenu = tk.OptionMenu(self.suboverlay_frame, self.current_sub_overlay, "None", *self.sub_overlay_names)
        self.select_suboverlay_optionmenu.pack(side=tk.LEFT)

        self.add_suboverlay_btn = tk.Button(self.suboverlay_frame, text="Add SubOverlay", command=self.load_suboverlay)
        self.add_suboverlay_btn.pack(side=tk.LEFT)

        self.clear_suboverlays_btn = tk.Button(self.suboverlay_frame, text="Clear SubOverlays", command=self.clear_suboverlays)
        self.clear_suboverlays_btn.pack(side=tk.LEFT)

        self.suboverlay_opacity_scale = tk.Scale(self.suboverlay_frame, from_=0, to=255, orient=tk.HORIZONTAL, label="SubOverlay Opacity")
        self.suboverlay_opacity_scale.bind("<Motion>", self.adjust_suboverlay_opacity)
        self.suboverlay_opacity_scale.pack(side=tk.LEFT)
        self.suboverlay_opacity_scale.config(from_=0, to=1, resolution=0.01)
        self.suboverlay_opacity_scale.set(0.4)

        self.reset_slice_btn = tk.Button(self.overlay_frame, text="Reset Slice", command=self.reset_to_middle_image)
        self.reset_slice_btn.pack(side=tk.LEFT, padx=5)
 
    def create_widget(self):

        frame_statusbar = tk.Frame(self.master, bd=1, relief = tk.SUNKEN)
        self.label_image_info = tk.Label(frame_statusbar, text="image info", anchor=tk.E, padx = 5)
        self.label_image_pixel = tk.Label(frame_statusbar, text="(x, y)", anchor=tk.W, padx = 5)
        self.label_image_info.pack(side=tk.RIGHT)
        self.label_image_pixel.pack(side=tk.LEFT)
        frame_statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Canvas
        self.canvas = tk.Canvas(self.master, background="black")
        self.canvas.pack(expand=True,  fill=tk.BOTH)  

        self.canvas.bind("<Button-1>", self.mouse_down_left)                   # MouseDown
        self.master.bind("<ButtonRelease-1>", self.mouse_up_left)              # MouseUp
        self.canvas.bind("<B1-Motion>", self.mouse_move_left)                  # MouseDrag
        self.canvas.bind("<Button-3>", self.mouse_down_right)                  # MouseDown
        self.master.bind("<ButtonRelease-3>", self.mouse_up_right)             # MouseUp
        self.canvas.bind("<B3-Motion>", self.mouse_move_right)                 # MouseDrag
        self.canvas.bind("<Motion>", self.mouse_move)                          # MouseMove
        self.canvas.bind("<Leave>", self.mouse_leave_canvas)                   # MouseLeave
        self.canvas.bind("<Double-Button-1>", self.mouse_double_click_left)    # MouseDoubleClick
        self.master.bind("<Control_L>", self.shift_press)
        self.master.bind("<KeyRelease-Control_L>", self.shift_release)
        self.master.bind("<Control_R>", self.shift_press)
        self.master.bind("<KeyRelease-Control_R>", self.shift_release)
        self.master.bind("<space>", lambda _: {self.overlay_visibility.set(not self.overlay_visibility.get()), self.redraw_image()})           # Spacebar
        self.master.bind("r", self.reset_to_middle_image)
        self.master.bind("c", self.toggle_color)

        
        if sys.platform == 'linux':  # Linux OS
            self.canvas.bind("<Button-4>", self.mouse_wheel)
            self.canvas.bind("<Button-5>", self.mouse_wheel)
        else:  # Windows OS
            self.master.bind("<MouseWheel>", self.mouse_wheel)

        # Bind left and right arrow keys for previous and next functionality
        self.master.bind("<Left>", self.show_previous_image)
        self.master.bind("<Right>", self.show_next_image)

    def show_help(self):
        help_message = textwrap.dedent("""
        Vesuvius Crackle Viewer Usage:

        - Open: Ctrl+O to open image.
        - Exit: Close the application.
        - Use the Ctrl key while dragging to draw on the overlay.
        - Double click to zoom fit.
        - Use the mouse wheel to zoom in/out.
        - Ctrl + Mouse wheel to rotate the image.
        - Space to toggle overlay visibility.
        - R to reset to the middle image.
        - C to toggle the drawing color.
        - Double click inside the image to reset the zoom, rotation and slice.

        Overlay Controls:
        - Load Overlay: Load an overlay image.
        - Create Empty Image: Create an empty overlay.
        - Save Overlay: Save the current overlay.
        - Save Combined Overlays: Save the combined image of the overlay and all sub-overlays.
        - Toggle Color: Switch between drawing colors.
        - Overlay Opacity: Adjust the opacity of the overlay.
        - Pick Color: Choose a custom drawing color.
        - Adjust the Pencil Size for drawing on the overlay.
        - Dropdown to select active overlay for drawing.
        - Add SubOverlay: Load one or multiple SubOverlay image. These images are displayed only and not mutable.
        - Clear SubOverlays: Clear all SubOverlays.
        - SubOverlay Opacity: Adjust the opacity of the SubOverlay.
        - Reset Slice: Reset to the middle image.
        """)
        tk.messagebox.showinfo("Help", help_message)

    def save_last_directory(self):
        with open("last_directory.txt", "w") as file:
            file.write(self.last_directory)

    def load_last_directory(self):
        try:
            with open("last_directory.txt", "r") as file:
                self.last_directory = file.read().strip()
        except FileNotFoundError:
            self.last_directory = None

    def load_images(self):
        initial_dir =self.last_directory if self.last_directory else os.getcwd()
        images_path = tk.filedialog.askdirectory(
            initialdir = initial_dir
        )
        if images_path:
            self.last_directory = images_path
            print(self.last_directory)
            self.images_folder = self.last_directory.rsplit('/', 1)[-1]
            self.save_last_directory()  # Save the last_directory
            self.image_list = sorted(glob.glob(os.path.join(self.last_directory, '*.tif')))
            self.image_index = len(self.image_list) // 2
            self.set_image(self.image_list[self.image_index])

    def load_overlay_image(self):
        initial_dir = os.path.dirname(self.last_directory) if self.last_directory else os.getcwd()
        try:
            file_path = tk.filedialog.askopenfilename(filetypes=[('PNG files', '*.png')], initialdir=initial_dir)
        except:
            file_path = tk.filedialog.askopenfilename(filetypes=[('PNG files', '*.png')], initialdir=os.getcwd())
        if file_path:
            print(file_path, self.last_directory)
            self.overlay_image = Image.open(file_path).convert("L").convert("1")
            if len(self.sub_overlays) == 0:
                self.sub_overlays.append(self.overlay_image)
            else:
                self.sub_overlays[0] = self.overlay_image
            self.redraw_image()
            # strip the file name from the path and save directory
            self.last_directory = file_path.rsplit('/', 1)[0] + "/" + self.images_folder
            self.sub_overlay_names[0] = file_path.rsplit('/', 1)[-1]
            self.update_suboverlay_dropdown()

    def create_empty_overlay_image(self):
        if not self.image_list:
            return
        reference_image = Image.open(self.image_list[0])
        width, height = reference_image.size
        # Changed from RGBA to 'L' for grayscale and set initial color to black
        self.overlay_image = Image.new("L", (width, height), "black").convert("1")
        if len(self.sub_overlays) == 0:
            self.sub_overlays.append(self.overlay_image)
        else:
            self.sub_overlays[0] = self.overlay_image
        self.sub_overlay_names[0] = "newly_created_overlay.png"
        self.update_suboverlay_dropdown()
        self.redraw_image()

    # Method to load SubOverlay
    def load_suboverlay(self):
        initial_dir = os.path.dirname(self.last_directory) if self.last_directory else os.getcwd()
        try:
            file_path = tk.filedialog.askopenfilename(filetypes=[('PNG files', '*.png')], initialdir=initial_dir)
        except:
            file_path = tk.filedialog.askopenfilename(filetypes=[('PNG files', '*.png')], initialdir=os.getcwd())
        if file_path:
            sub_overlay = Image.open(file_path).convert("L").convert("1")
            self.sub_overlays.append(sub_overlay)
            self.redraw_image()
            # strip the file name from the path and save directory
            self.last_directory = file_path.rsplit('/', 1)[0] + "/" + self.images_folder
            self.sub_overlay_names.append(file_path.rsplit('/', 1)[-1])
            if len(self.sub_overlay_names) >= len(self.sub_overlay_colors):
                self.sub_overlay_colors.append(self.sub_overlay_colors[len(self.sub_overlay_colors)-1])
            self.update_suboverlay_dropdown()

    def update_suboverlay_dropdown(self):
        menu = self.select_suboverlay_optionmenu['menu']
        menu.delete(0, 'end')
        new_choices = self.sub_overlay_names
        for choice in new_choices:
            menu.add_command(label=choice, command=tk._setit(self.current_sub_overlay, choice))

    def suboverlay_selected(self, *args):
        selected_name = self.current_sub_overlay.get()
        try:
            selected_index = self.sub_overlay_names.index(selected_name)

            # Swap the 0-th element with the selected_index element
            name0, name1 = self.sub_overlay_names[selected_index], self.sub_overlay_names[0]
            self.sub_overlay_names[0], self.sub_overlay_names[selected_index] = name0, name1

            # Swap the 0-th element with the selected_index element for colors as well
            color0, color1 = self.sub_overlay_colors[selected_index], self.sub_overlay_colors[0]
            self.sub_overlay_colors[0], self.sub_overlay_colors[selected_index] = color0, color1

            # Swap the 0-th element with the selected_index element for sub_overlays as well
            sub_overlay0, sub_overlay1 = self.sub_overlays[selected_index], self.sub_overlays[0]
            self.sub_overlays[0], self.sub_overlays[selected_index] = sub_overlay0, sub_overlay1

            self.overlay_image = self.sub_overlays[0]
            
            # Update the dropdown
            self.update_suboverlay_dropdown()
            
            # Set the current value to the new 0-th element
            self.current_sub_overlay.set(self.sub_overlay_names[0])

            self.redraw_image()
            self.toggle_color()
            self.toggle_color()

        except ValueError:
            print("Selected value is not in the list.")


    def save_overlay(self):
        if self.overlay_image:
            initial_dir = os.path.dirname(self.last_directory) if self.last_directory else os.getcwd()
            try:
                save_path = tk.filedialog.asksaveasfilename(filetypes=[('PNG files', '*.png')], initialdir=initial_dir)
            except:
                save_path = tk.filedialog.asksaveasfilename(filetypes=[('PNG files', '*.png')], initialdir=os.getcwd())
            
            if save_path:
                # Convert to grayscale and remove alpha channel
                bw_image = self.overlay_image.convert("1")
                bw_image.save(save_path)
                # strip the file name from the path and save directory
                self.last_directory = save_path.rsplit('/', 1)[0] + "/" + self.images_folder

    def save_combined_overlays(self):
        if self.pil_image:
            # Create a base image
            combined = Image.new("L", (self.pil_image.width, self.pil_image.height), color="black")

            # Add sub-overlays
            for sub_overlay in self.sub_overlays:
                combined = ImageChops.lighter(combined, sub_overlay.convert("L"))

            # Add the main overlay
            if self.overlay_image:
                combined = ImageChops.lighter(combined, self.overlay_image.convert("L"))

            # Save the combined image in grayscale and without an alpha channel
            initial_dir = os.path.dirname(self.last_directory) if self.last_directory else os.getcwd()
            try:
                save_path = tk.filedialog.asksaveasfilename(filetypes=[('PNG files', '*.png')], initialdir=initial_dir)
            except:
                save_path = tk.filedialog.asksaveasfilename(filetypes=[('PNG files', '*.png')], initialdir=os.getcwd())

            if save_path:
                bw_combined = combined.convert("1")
                bw_combined.save(save_path)
                # strip the file name from the path and save directory
                self.last_directory = save_path.rsplit('/', 1)[0] + "/" + self.images_folder

    def toggle_overlay(self):
        self.redraw_image()

    def adjust_overlay_opacity(self, event=None):
        self.overlay_opacity_entry.delete(0, tk.END)
        self.overlay_opacity_entry.insert(tk.END, f"{self.overlay_opacity_scale.get():.2f}")
        self.redraw_image()

    def adjust_suboverlay_opacity(self, event=None):
        self.redraw_image()

    def set_opacity_from_entry(self, event=None):
        try:
            val = float(self.overlay_opacity_entry.get())
            if 0 <= val <= 1:
                self.overlay_opacity_scale.set(val)
                self.adjust_overlay_opacity()
        except ValueError:
            pass

    def pick_color(self):
        color = tkinter.colorchooser.askcolor(title="Choose Overlay Color")
        if color and color[1]:
            self.sub_overlay_colors[0] = color[1]

        self.toggle_color()
        self.toggle_color()
        self.redraw_image()

    def toggle_color(self, event=None):
        self.pencil_color = 'white' if self.pencil_color == 'black' else 'black'
        label_color = 'black' if self.pencil_color == 'black' else self.sub_overlay_colors[0]
        self.color_label.config(background=label_color) # Update the color preview$
        
    def set_image(self, filename):
        if not filename:
            return

        self.pil_image = Image.open(filename)
        # Convert to 8-bit and grayscale
        self.pil_image = Image.fromarray(np.uint8(np.array(self.pil_image)//256)).convert("L")
        self.draw_image(self.pil_image)

        self.master.title(self.my_title + " - " + os.path.basename(filename))
        self.label_image_info["text"] = f"{self.pil_image.format} : {self.pil_image.width} x {self.pil_image.height} {self.pil_image.mode}"
        os.chdir(os.path.dirname(filename))

    # Method to clear all SubOverlays
    def clear_suboverlays(self):
        self.sub_overlays = [self.sub_overlays[0]]
        self.sub_overlay_names = [self.sub_overlay_names[0]]
        self.redraw_image()
        self.update_suboverlay_dropdown()

    def reset_to_middle_image(self, event=None):
        self.image_index = len(self.image_list) // 2
        self.set_image(self.image_list[self.image_index])


    def show_previous_image(self, event):
        if self.image_index > 0:
            self.image_index -= 1
            self.set_image(self.image_list[self.image_index])

    def show_next_image(self, event):
        if self.image_index < len(self.image_list) - 1:
            self.image_index += 1
            self.set_image(self.image_list[self.image_index])

    def mouse_down_left(self, event):
        self.__old_event = event
        self.mouse_is_pressed = True  # Mouse button pressed

    def mouse_up_left(self, event):  
        self.mouse_is_pressed = False  # Mouse button released

    def mouse_down_right(self, event):
        self.__old_event = event
        self.mouse_is_pressed_right = True  # Mouse button pressed

    def mouse_up_right(self, event):  
        self.mouse_is_pressed_right = False  # Mouse button released

    def mouse_move_left(self, event):
        if (self.pil_image == None) or (not self.mouse_is_pressed): # Check if mouse button is pressed
            return

        # Check if shift is pressed and mouse is dragged to draw
        if self.shift_pressed and self.mouse_is_pressed and self.overlay_image:
            draw = ImageDraw.Draw(self.overlay_image)
            old_point = tuple(self.to_image_point(self.__old_event.x, self.__old_event.y)[:2])
            new_point = tuple(self.to_image_point(event.x, event.y)[:2])
            width = self.size_scale.get()
            draw.line([old_point, new_point], fill=self.pencil_color, width=width, joint='curve')
            # Draw circle with radius with/2
            draw.ellipse([old_point[0]-width/2, old_point[1]-width/2, old_point[0]+width/2, old_point[1]+width/2], fill=self.pencil_color)
            draw.ellipse([new_point[0]-width/2, new_point[1]-width/2, new_point[0]+width/2, new_point[1]+width/2], fill=self.pencil_color)
        else: # Else case for dragging
            self.translate(event.x - self.__old_event.x, event.y - self.__old_event.y)

        self.redraw_image()
        self.__old_event = event

    def mouse_move_right(self, event):
        if (self.pil_image == None) or (not self.mouse_is_pressed_right): # Check if mouse button is pressed
            return

        draw = ImageDraw.Draw(self.overlay_image)
        old_point = tuple(self.to_image_point(self.__old_event.x, self.__old_event.y)[:2])
        new_point = tuple(self.to_image_point(event.x, event.y)[:2])
        width = self.size_scale.get()
        draw.line([old_point, new_point], fill=self.pencil_color, width=width, joint='curve')
        # Draw circle with radius with/2
        draw.ellipse([old_point[0]-width/2, old_point[1]-width/2, old_point[0]+width/2, old_point[1]+width/2], fill=self.pencil_color)
        draw.ellipse([new_point[0]-width/2, new_point[1]-width/2, new_point[0]+width/2, new_point[1]+width/2], fill=self.pencil_color)

        self.redraw_image()
        self.__old_event = event

    def mouse_move(self, event):
        # Remove the old circle if it exists
        if self.cursor_circle:
            self.canvas.delete(self.cursor_circle)
        
        # Draw the new circle
        x, y = event.x, event.y
        # Extract scaling factor from the affine matrix
        try:
            scaling_factor = self.mat_affine[0, 0]
        except:
            scaling_factor = 1

        r = (self.size_scale.get() * scaling_factor)// 2  # radius of circle
        self.cursor_circle = self.canvas.create_oval(x-r, y-r, x+r, y+r, outline=self.pencil_color)

        if (self.pil_image == None):
            return
        
        image_point = self.to_image_point(event.x, event.y)
        if image_point != []:
            self.label_image_pixel["text"] = (f"({image_point[0]:.2f}, {image_point[1]:.2f})")
        else:
            self.label_image_pixel["text"] = ("(--, --)")

    def mouse_leave_canvas(self, event):
        if self.cursor_circle:
            self.canvas.delete(self.cursor_circle)
            self.cursor_circle = None


    def mouse_double_click_left(self, event):
        if self.pil_image == None:
            return
        self.zoom_fit(self.pil_image.width, self.pil_image.height)
        self.redraw_image()
        self.reset_to_middle_image()

    def shift_press(self, event):
        self.shift_pressed = True

    def shift_release(self, event):
        self.shift_pressed = False

    def mouse_wheel(self, event):
        if self.pil_image == None:
            return

        if event.num == 5 or event.delta < 0:
            scale_factor = 0.8 if not self.shift_pressed else -5
        else: # event.num == 4 or event.delta > 0
            scale_factor = 1.25 if not self.shift_pressed else 5

        if not self.shift_pressed: 
            self.scale_at(scale_factor, event.x, event.y)
        else:
            self.rotate_at(scale_factor, event.x, event.y)
        self.redraw_image() # redraw the image

    def reset_transform(self):
        self.mat_affine = np.eye(3) 

    def translate(self, offset_x, offset_y):
        mat = np.eye(3)
        mat[0, 2] = float(offset_x)
        mat[1, 2] = float(offset_y)

        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale(self, scale:float):
        mat = np.eye(3)
        mat[0, 0] = scale
        mat[1, 1] = scale

        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale_at(self, scale:float, cx:float, cy:float):

        self.translate(-cx, -cy)
        self.scale(scale)
        self.translate(cx, cy)

    def rotate(self, deg:float):
        mat = np.eye(3) 
        mat[0, 0] = math.cos(math.pi * deg / 180)
        mat[1, 0] = math.sin(math.pi * deg / 180)
        mat[0, 1] = -mat[1, 0]
        mat[1, 1] = mat[0, 0]

        self.mat_affine = np.dot(mat, self.mat_affine)

    def rotate_at(self, deg:float, cx:float, cy:float):

        self.translate(-cx, -cy)
        self.rotate(deg)
        self.translate(cx, cy)

    def zoom_fit(self, image_width, image_height):

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if (image_width * image_height <= 0) or (canvas_width * canvas_height <= 0):
            return

        self.reset_transform()

        scale = 1.0
        offsetx = 0.0
        offsety = 0.0

        if (canvas_width * image_height) > (image_width * canvas_height):
            scale = canvas_height / image_height
            offsetx = (canvas_width - image_width * scale) / 2
        else:
            scale = canvas_width / image_width
            offsety = (canvas_height - image_height * scale) / 2

        self.scale(scale)
        self.translate(offsetx, offsety)

    def to_image_point(self, x, y):
        if self.pil_image == None:
            return []
        mat_inv = np.linalg.inv(self.mat_affine)
        image_point = np.dot(mat_inv, (x, y, 1.))
        if  image_point[0] < 0 or image_point[1] < 0 or image_point[0] > self.pil_image.width or image_point[1] > self.pil_image.height:
            return []

        return image_point


    def draw_image(self, pil_image):
        
        if pil_image == None:
            return

        self.pil_image = pil_image

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        mat_inv = np.linalg.inv(self.mat_affine)

        affine_inv = (
            mat_inv[0, 0], mat_inv[0, 1], mat_inv[0, 2],
            mat_inv[1, 0], mat_inv[1, 1], mat_inv[1, 2]
            )

        dst = self.pil_image.transform(
                    (canvas_width, canvas_height),
                    Image.AFFINE,   
                    affine_inv,   
                    Image.NEAREST   
                    )
        
        if dst.mode != 'RGBA':
            dst = dst.convert('RGBA')

        if self.overlay_visibility.get():
            # Overlaying SubOverlays
            for i, sub_overlay in enumerate(self.sub_overlays):
                if i == 0: continue # skip overlay image

                sub_overlay_transformed = sub_overlay.transform(
                    (canvas_width, canvas_height),
                    Image.AFFINE,
                    affine_inv,
                    Image.NEAREST
                )
                
                # Ensure the image is RGBA (has an alpha channel)
                if sub_overlay_transformed.mode != 'RGBA':
                    sub_overlay_transformed = sub_overlay_transformed.convert('RGBA')

                r, g, b, a = sub_overlay_transformed.split()
                grayscale = sub_overlay_transformed.convert("L")
                alpha = grayscale  # Use grayscale directly, without inverting
                sub_overlay_color = Image.new('RGB', sub_overlay_transformed.size, self.sub_overlay_colors[i])
                final_sub_overlay = Image.composite(sub_overlay_color, sub_overlay_transformed, grayscale)
                final_sub_overlay.putalpha(alpha)

                # Adjust the opacity based on the value of the slider
                alpha = ImageEnhance.Brightness(alpha).enhance(self.suboverlay_opacity_scale.get())
                final_sub_overlay.putalpha(alpha)

                dst.paste(final_sub_overlay, (0, 0), final_sub_overlay)

        # Overlaying the additional PNG
        if self.overlay_visibility.get() and self.overlay_image:
            overlay_transformed = self.overlay_image.transform(
                (canvas_width, canvas_height),
                Image.AFFINE,
                affine_inv,
                Image.NEAREST
            )
            
            # Ensure the image is RGBA (has an alpha channel)
            if overlay_transformed.mode != 'RGBA':
                overlay_transformed = overlay_transformed.convert('RGBA')

            r, g, b, a = overlay_transformed.split()
            grayscale = overlay_transformed.convert("L")
            alpha = grayscale  # Use grayscale directly, without inverting
            yellow = Image.new('RGB', overlay_transformed.size, self.sub_overlay_colors[0])
            final_overlay = Image.composite(yellow, overlay_transformed, grayscale)
            final_overlay.putalpha(alpha)

            # Adjust the opacity based on the value of the slider
            alpha = ImageEnhance.Brightness(alpha).enhance(self.overlay_opacity_scale.get())
            final_overlay.putalpha(alpha)

            dst.paste(final_overlay, (0, 0), final_overlay)

        im = ImageTk.PhotoImage(image=dst)

        item = self.canvas.create_image(
                0, 0, 
                anchor='nw',
                image=im  
                )

        self.image = im

    def redraw_image(self):
        if self.pil_image == None:
            return
        self.draw_image(self.pil_image)


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()
