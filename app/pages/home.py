import dash

from dash import html
from datetime import datetime

dash.register_page(__name__, path="/", order=0)

def layout(**kwargs):
    return html.Div(
        [
            html.Div(
                className="nav-header",
            ),
            html.Div(
                className="body",
                children=[
                    html.P("Treehouse: Metrics Datastore"),
                ]
            ),            
        ])