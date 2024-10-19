import dash

from dash import html
from datetime import datetime

dash.register_page(__name__, path="/")

def layout(**kwargs):
    return html.Div(
        [
            html.H1('Projects'),
            html.Div(
                className="nav-header",
                children=[]
            ),
            html.Div(
                className="body",
                children=[]
            ),            
        ])