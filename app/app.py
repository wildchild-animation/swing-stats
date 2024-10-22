import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
import dash
import dash_bootstrap_components as dbc

import plotly.io as pio

from datetime import datetime

from dash import Dash, html, dcc, callback, Output, Input, Patch

import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

# adds  templates to plotly.io
load_figure_template(["darkly", "sandstone"])

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.MINTY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=False,
    prevent_initial_callbacks=True,
)

color_mode_switch =  html.Span(
    [
        dbc.Label(className="fa fa-moon", html_for="switch"),
        dbc.Switch( id="switch", value=True, className="d-inline-block ms-1", persistence=True),
        dbc.Label(className="fa fa-sun", html_for="switch"),
    ]
)

app.layout = dbc.Container(
    [
        html.Div(
            className="app-header",
            children=[
##                color_mode_switch
            ],
        ),
        html.Div(
            className="nav-header",
            children=[
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Nav(
                                [
                                    dbc.NavItem(
                                        dbc.NavLink(
                                            # f"{page['name']} - {page['path']}",
                                            f"{page['name']}", href=page["relative_path"],
                                        )
                                    )
                                    for page in dash.page_registry.values()
                                ],
                                pills=True,
                            ),
                            width=12,
                        )
                    ]
                ),
            ],
        ),
        html.Div(
            className="body",
            children=[
                dbc.Row([dbc.Col(dash.page_container, width=12)]),
            ],
        ),
        html.Div(
            className="footer",
            children=[
                html.P(
                    [
                        f"Current Time: {datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}",
                        html.Br(),
                        f"© {datetime.now().year} - wild child animation",
                    ]
                )
            ],
        ),        
    ],
    fluid=True,
)

@callback(
    Output("graph", "figure"),
    Input("color-mode-switch", "value"),
)
def update_figure_template(switch_on):
    # When using Patch() to update the figure template, you must use the figure template dict
    # from plotly.io  and not just the template name
    template = pio.templates["darkly"] if switch_on else pio.templates["sandstone"]

    patched_figure = Patch()
    patched_figure["layout"]["template"] = template
    return patched_figure

if __name__ == "__main__":
    app.run(debug=False, port=80, host="0.0.0.0")
