"""
Provides custom Tkinter/CustomTkinter widgets for displaying HTML-formatted text
arranged in tables or scrollable frames.

Classes:
    SimpleHTMLParser: Parses basic HTML tags for Tkinter Text widgets.
    RichTextLabel: A read-only text widget supporting basic HTML formatting.
    AutoScrollableFrame: A frame that toggles scrollbar visibility based on content.
    RichTextTable: A structural component for header/rows/footer layout.
    ScrollableInfoTable: The main composite widget combining scrolling and table layout.

@file info_widget.py
@copyright SPDX-FileCopyrightText: Copyright 2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import tkinter as tk
from html.parser import HTMLParser
import customtkinter as ctk


class SimpleHTMLParser(HTMLParser):
    """
    Parses basic HTML tags (b, i, u) and applies corresponding Tkinter text tags.
    """

    def __init__(self, text_widget, font_family, font_size):
        """
        Initialize the parser with target widget and font settings.

        Args:
            text_widget (tk.Text): The text widget to insert parsed content into.
            font_family (str): Font family for the tags.
            font_size (int): Font size for the tags.
        """
        super().__init__()
        self.text_widget = text_widget
        self.active_tags = []

        self.text_widget.tag_configure("bold", font=(font_family, font_size, "bold"))
        self.text_widget.tag_configure("italic", font=(font_family, font_size, "italic"))
        self.text_widget.tag_configure("underline", underline=True)
        self.text_widget.tag_configure("bold_italic", font=(font_family, font_size, "bold italic"))


    def handle_starttag(self, tag, attrs):
        """Track active styling tags."""
        if tag in ["b", "i", "u"]:
            self.active_tags.append(tag)


    def handle_endtag(self, tag):
        """Remove tags from active list upon closing."""
        if tag in ["b", "i", "u"]:
            if tag in self.active_tags:
                self.active_tags.remove(tag)


    def handle_data(self, data):
        """Insert text with currently active style tags."""
        if not data:
            return
        tags = []
        if "b" in self.active_tags:
            tags.append("bold")
        if "i" in self.active_tags:
            tags.append("italic")
        if "u" in self.active_tags:
            tags.append("underline")

        # Combine tags if necessary (Tkinter requires specific font definitions for combinations)
        if "bold" in tags and "italic" in tags:
            tags.remove("bold")
            tags.remove("italic")
            tags.append("bold_italic")

        self.text_widget.insert("end", data, tuple(tags))


class RichTextLabel(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    """
    A read-only Text widget wrapped in a Frame, capable of rendering simple HTML
    and automatically adjusting its height to fit the content.
    """

    def __init__(self, master, text="", font_size=11, text_color=None, bg_color=None, width_chars=30, **kwargs): # pylint: disable=line-too-long, too-many-arguments, too-many-positional-arguments
        """
        Initialize the RichTextLabel.

        Args:
            master: Parent widget.
            text (str): HTML formatted text to display.
            font_size (int): Base font size.
            text_color (str): Text color (optional, auto-detected if None).
            bg_color (str): Background color (optional).
            width_chars (int): Width of the widget in characters.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color=bg_color, **kwargs)

        if text_color is None:
            text_color = "black" if ctk.get_appearance_mode() == "Light" else "white"

        if bg_color is None:
            bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]

        resolved_bg_hex = self._apply_appearance_mode(bg_color)

        self.text_widget = tk.Text(
            self,
            font=("Arial", font_size),
            fg=text_color,
            bg=resolved_bg_hex,
            bd=0,
            highlightthickness=0,
            wrap="word",
            height=1,
            width=width_chars,
            padx=0, pady=0
        )
        self.text_widget.pack(fill="both", expand=True, anchor="nw")

        parser = SimpleHTMLParser(self.text_widget, "Arial", font_size)
        parser.feed(text)
        self.text_widget.configure(state="disabled", cursor="arrow")


    def fit_height(self):
        """
        Adjusts the widget height based on the number of display lines.
        Ignores resizing if the widget is not yet rendered (width < 10).
        """
        if self.winfo_width() < 10:
            return
        try:
            num_lines = self.text_widget.count("1.0", "end", "displaylines")
            lines = int(num_lines[0]) if num_lines else 1
            self.text_widget.configure(height=lines)
        except Exception: # pylint: disable=broad-exception-caught
            pass


class AutoScrollableFrame(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    """
    A frame that automatically shows or hides a vertical scrollbar depending on
    whether the content exceeds the visible area.
    """

    def __init__(self, master, fg_color=None, **kwargs):
        """
        Initialize the AutoScrollableFrame.

        Args:
            master: Parent widget.
            fg_color: Foreground color (background of the frame).
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.bg_color = fg_color
        if self.bg_color is None:
            self.bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]

        canvas_bg_hex = self._apply_appearance_mode(self.bg_color)

        self.canvas = tk.Canvas(self, highlightthickness=0, bg=canvas_bg_hex, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_content = ctk.CTkFrame(self.canvas, fg_color=self.bg_color)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw") # pylint: disable=line-too-long

        self.scrollable_content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self._on_mouse_wheel)


    def _on_content_configure(self, _event):
        """Update scroll region when content changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._check_scrollbar()


    def _on_canvas_configure(self, event):
        """Ensure the inner frame matches the canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self._check_scrollbar()


    def _check_scrollbar(self):
        """Toggle scrollbar visibility based on content vs canvas height."""
        try:
            if self.scrollable_content.winfo_reqheight() > self.canvas.winfo_height():
                if not self.scrollbar.winfo_ismapped():
                    self.scrollbar.grid(row=0, column=1, sticky="ns")
            else:
                if self.scrollbar.winfo_ismapped():
                    self.scrollbar.grid_forget()
        except Exception: # pylint: disable=broad-exception-caught
            pass


    def _on_mouse_wheel(self, event):
        """
        Handle mouse wheel scrolling.
        Wrapped in try-except to prevent TclError (bad window path) when bind_all
        triggers on destroyed widgets.
        """
        try:
            if self.scrollbar.winfo_ismapped():
                if event.num == 5 or event.delta < 0:
                    self.canvas.yview_scroll(1, "units")
                elif event.num == 4 or event.delta > 0:
                    self.canvas.yview_scroll(-1, "units")
        except Exception: # pylint: disable=broad-exception-caught
            pass


class RichTextTable(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    """
    Renders a data structure (Header -> Rows -> Footer) using RichTextLabels.
    Manages column widths dynamically based on data['col_widths'] or constructor defaults.
    """

    def __init__(self, master, data, font_size=11, col1_width=None, col2_width=None, fg_color=None, **kwargs): # pylint: disable=line-too-long, too-many-arguments, too-many-positional-arguments
        """
        Initialize the RichTextTable.

        Args:
            master: Parent widget.
            data (dict): Dictionary containing 'header', 'rows' (list of tuples), 'footer',
                         and optional 'col_widths'.
            font_size (int): Font size for the text.
            col1_width (int): Minimum width for the first column.
            col2_width (int): Minimum width for the second column.
            fg_color: Background color.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.font_size = font_size
        self.managed_labels = []

        self.default_col1_width = col1_width
        self.default_col2_width = col2_width

        if fg_color is None:
            fg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        self.bg_color = fg_color

        self.text_color = "black" if ctk.get_appearance_mode() == "Light" else "white"

        self._build_ui(data)


    def _apply_column_config(self, col1_width, col2_width):
        """Applies grid configuration for columns."""
        if col1_width is None and col2_width is None:
            # 50% / 50% split
            self.grid_columnconfigure(0, weight=1, uniform="equal_cols", minsize=0)
            self.grid_columnconfigure(1, weight=1, uniform="equal_cols", minsize=0)
        else:
            # Disable uniform grouping by setting it to empty string to allow custom weights
            w0, min0 = (0, col1_width) if col1_width is not None else (1, 0)
            w1, min1 = (0, col2_width) if col2_width is not None else (1, 0)

            self.grid_columnconfigure(0, weight=w0, minsize=min0, uniform="")
            self.grid_columnconfigure(1, weight=w1, minsize=min1, uniform="")


    def _build_ui(self, data):
        """Constructs the table rows from the provided data dictionary."""
        # 1. Check if data overrides column widths
        widths = data.get("col_widths")
        if widths and isinstance(widths, (list, tuple)) and len(widths) == 2:
            self._apply_column_config(widths[0], widths[1])
        else:
            self._apply_column_config(self.default_col1_width, self.default_col2_width)

        current_row = 0

        # 2. Header
        if header_text := data.get("header"):
            lbl = RichTextLabel(self, text=header_text, font_size=self.font_size + 2,
                                text_color=self.text_color, bg_color=self.bg_color, width_chars=1)
            lbl.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=(0, 10), pady=(0, 5)) # pylint: disable=line-too-long
            self.managed_labels.append(lbl)
            current_row += 1

        # 3. Key-Value Rows
        for key_text, value_text in data.get("rows", []):
            var_lbl = RichTextLabel(self, text=key_text, font_size=self.font_size,
                                    text_color=self.text_color, bg_color=self.bg_color, width_chars=10) # pylint: disable=line-too-long
            var_lbl.grid(row=current_row, column=0, sticky="new", padx=(0, 10), pady=(2, 0))
            self.managed_labels.append(var_lbl)

            val_lbl = RichTextLabel(self, text=value_text, font_size=self.font_size,
                                    text_color=self.text_color, bg_color=self.bg_color, width_chars=5) # pylint: disable=line-too-long
            val_lbl.grid(row=current_row, column=1, sticky="new", padx=10, pady=(2, 0))
            self.managed_labels.append(val_lbl)
            current_row += 1

        # 4. Footer
        if footer_text := data.get("footer"):
            # Use default text color (same as rows) unless overridden elsewhere
            lbl = RichTextLabel(self, text=footer_text, font_size=self.font_size,
                                text_color=self.text_color, bg_color=self.bg_color, width_chars=1)
            lbl.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=(0, 10), pady=(10, 5)) # pylint: disable=line-too-long
            self.managed_labels.append(lbl)


    def set_data(self, data):
        """
        Replaces the current table content with new data and refreshes layout.
        """
        for widget in self.winfo_children():
            widget.destroy()

        self.managed_labels.clear()
        self._build_ui(data)
        self.update_layout()


    def update_layout(self):
        """
        Refreshes the height of all child labels to fit their content.
        Should be called when the container is resized or data changes.
        """
        for lbl in self.managed_labels:
            lbl.fit_height()


class ScrollableInfoTable(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    """
    High-level widget that integrates the AutoScrollableFrame with the RichTextTable.
    Supports rounded corners via 'corner_radius' which adds internal padding to prevent clipping.
    """

    def __init__(self, master, data, font_size=11, col1_width=None, col2_width=None, fg_color=None, corner_radius=None, **kwargs): # pylint: disable=line-too-long, too-many-arguments, too-many-positional-arguments
        """
        Initialize the ScrollableInfoTable.

        Args:
            master: Parent widget.
            data: Data dictionary for the table.
            font_size (int): Font size.
            col1_width, col2_width: Column widths.
            fg_color: Background color.
            corner_radius (int): Corner radius for the frame.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color=fg_color, corner_radius=corner_radius, **kwargs)

        self._resize_job = None

        if fg_color is None:
            fg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]

        # Calculate padding to prevent inner square canvas from overlapping rounded corners
        inner_pad = 0
        if corner_radius is not None and isinstance(corner_radius, (int, float)) and corner_radius > 0: # pylint: disable=line-too-long
            # Approx 0.3-0.4 * radius is needed to clear the corner visually.
            # We enforce a minimum padding if radius is present.
            inner_pad = max(5, int(corner_radius * 0.4))

        self.scroll_frame = AutoScrollableFrame(self, fg_color=fg_color)
        # Apply padding to the inner frame so the parent's rounded corners are visible
        self.scroll_frame.pack(fill="both", expand=True, padx=inner_pad, pady=inner_pad)

        self.scroll_frame.scrollable_content.grid_columnconfigure(0, weight=1)

        self.table = RichTextTable(
            self.scroll_frame.scrollable_content,
            data=data,
            font_size=font_size,
            col1_width=col1_width,
            col2_width=col2_width,
            fg_color=fg_color
        )
        self.table.grid(row=0, column=0, sticky="nsew")

        self.scroll_frame.scrollable_content.bind("<Configure>", self._schedule_layout_update)


    def _schedule_layout_update(self, _event):
        """Debounce layout updates to avoid performance issues during resize."""
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(50, self._perform_layout_update)


    def _perform_layout_update(self):
        self.table.update_layout()


    def update_data(self, data):
        """
        Updates the table with new data.
        Supports 'col_widths': (w1, w2) in data dictionary to override layout.
        """
        self.table.set_data(data)
