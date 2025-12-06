import customtkinter as ctk
import resort_theme as theme


class CTkMultiSelectDropdown(ctk.CTkFrame):
    def __init__(self, parent, values=None, command=None, width=240, **kwargs):
        super().__init__(parent, **kwargs)

        self.values = values or []
        self.command = command
        self.selected = set()

        self.dropdown_btn = ctk.CTkButton(
            self,
            text="Select...",
            fg_color=theme.PRIMARY,
            width=width,
            command=self.toggle_menu
        )
        self.dropdown_btn.pack(fill="x")

        # Dropdown menu frame
        self.menu_frame = ctk.CTkFrame(self, corner_radius=6)
        self.menu_shown = False

        self.check_vars = {}
        self.checkboxes = []

        for val in self.values:
            var = ctk.BooleanVar()
            chk = ctk.CTkCheckBox(
                self.menu_frame,
                text=val,
                variable=var,
                command=self.on_select
            )
            chk.pack(anchor="w", padx=10, pady=2)
            self.check_vars[val] = var
            self.checkboxes.append(chk)

    def toggle_menu(self):
        if self.menu_shown:
            self.menu_frame.pack_forget()
            self.menu_shown = False
        else:
            self.menu_frame.pack(fill="x", pady=4)
            self.menu_shown = True

    def on_select(self):
        self.selected = {k for k, v in self.check_vars.items() if v.get()}

        count = len(self.selected)

        if count == 0:
            text = "Select..."
        elif count == 1:
            text = next(iter(self.selected))
        else:
            text = f"{count} selected"

        self.dropdown_btn.configure(text=text)

        if self.command:
            self.command(list(self.selected))

    def set_values(self, values):
        # Update items dynamically
        self.values = values

        # destroy previous checkboxes
        for chk in self.checkboxes:
            chk.destroy()
        self.checkboxes.clear()
        self.check_vars.clear()

        # Clear previous selection state
        self.selected = set()
        # Reset button label
        self.dropdown_btn.configure(text="Select...")

        for val in self.values:
            var = ctk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(
                self.menu_frame,
                text=val,
                variable=var,
                command=self.on_select
            )
            chk.pack(anchor="w", padx=10, pady=2)
            self.check_vars[val] = var
            self.checkboxes.append(chk)

    def get_selected(self):
        return list(self.selected)