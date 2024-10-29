import flet as ft

def main(page: ft.Page):
    def button_clicked(e):
        p.value = f"Values: '{persona.value}', '{industry.value}', '{email.value}'"
        page.update()

    p = ft.Text()
    b = ft.ElevatedButton(text="Generate", on_click=button_clicked)
    persona = ft.Dropdown(
        width=500,
        label="Persona",
        options=[
            ft.dropdown.Option("CXO"),
            ft.dropdown.Option("Dev"),
        ],
    )
    industry = ft.Dropdown(
        width=500,
        label="Industry",
        options=[
            ft.dropdown.Option("Financial"),
            ft.dropdown.Option("Retail"),
        ],
    )
    email = ft.TextField(
        width=500,
        label="E-Mail"
    )
    page.add(persona, industry, email, b, p)

ft.app(main)