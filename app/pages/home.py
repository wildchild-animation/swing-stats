import dash

from dash import html
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/", order=0)

def layout(**kwargs):
    return html.Div(
        [
            html.Div(
                className="nav-header",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H2("Treehouse: Metrics Datastore", className="card-title"),
                    ]
                ),
                color="info",
                inverse=True,
                className="mb-2"
            ),          
            html.Div(
                className="body",
                children=[
                ]
            ),            
        ])