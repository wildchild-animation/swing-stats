import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
import dash
import dash_bootstrap_components as dbc

from dash import Dash, html, dcc

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.SPACELAB],
    suppress_callback_exceptions=False,
    prevent_initial_callbacks=True,
)

app.layout = dbc.Container(
    [
        html.Div(
            className="app-header",
            children=[
                dbc.Row([dbc.Col(html.H1("Treehouse: Dash Pages"), className="mb-4")]),
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
                                            f"{page['name']} - {page['path']}",
                                            href=page["relative_path"],
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
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=False)
