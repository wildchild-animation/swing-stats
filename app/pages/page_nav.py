from dash import dcc, html
import dash_bootstrap_components as dbc

def get_nav_filters(
    prefix: str,
    project_list=None,
    department_list=None,
    task_type_list=None,
    task_status_list=None,
    artist_list=None,
    episode_list=None,

    additional_children=[],
):
    children = []

    if project_list is not None:
        children.append(
            html.Div(
                dcc.Dropdown(
                    project_list,
                    value=project_list,
                    id=f"{prefix}_project_combo",
                    multi=True,
                ),
            )
        )

    if department_list is not None:
        children.append(
            html.Div(
                dcc.Dropdown(
                    department_list,
                    value=department_list,
                    id=f"{prefix}_department_combo",
                    multi=True,
                ),
            )
        )

    if task_type_list is not None:
        children.append(
            html.Div(
                dcc.Dropdown(
                    task_type_list,
                    value=task_type_list,
                    id=f"{prefix}_task_type_combo",
                    multi=True,
                ),
            )
        )

    if task_status_list is not None:
        children.append(
            html.Div(
                dcc.Dropdown(
                    task_status_list,
                    value=task_status_list,
                    id=f"{prefix}_task_status_combo",
                    multi=True,
                ),
            )
        )

    if episode_list is not None:
        children.append(
            get_episode_filter(prefix, episode_list)
        )

    if artist_list is not None:
        children.append(
            html.Div(
                id=f"{prefix}_artist_filter",
                children=[
                    dcc.Dropdown(
                        artist_list,
                        value=artist_list,
                        id=f"{prefix}_artist_combo",
                        multi=True,
                    )
                ],
            )
        )        

    children.extend(additional_children)

    return html.Div(
        className="nav-header",
        children=[
            html.Div(
                children=children,
            ),
        ],
    )

def get_episode_filter(prefix: str, episode_list=None):
        
    return html.Div(
            id=f"{prefix}_episode_filter",
            children=[
                dcc.Dropdown(
                    episode_list,
                    value=episode_list,
                    id=f"{prefix}_episode_combo",
                    multi=True,
                )
            ],
        )    


def get_task_filters(prefix: str):
        
    return[
        dbc.Button(
            "Due Last Week",
            id=f"{prefix}_tasks_last_week",
            n_clicks=0,
            style={"bg_color": "error"},
            size="sm",
            className="mr-2",
        ),
        dbc.Button(
            "Now",
            id=f"{prefix}_tasks_now",
            n_clicks=0,
            color="success",
            size="sm",
            className="mr-2",
        ),
        dbc.Button(
            "Reset",
            id=f"{prefix}_tasks_reset",
            n_clicks=0,
            color="info",
            size="sm",
            className="mr-2",
        ),
        dbc.Button(
            "Next Week",
            id=f"{prefix}_tasks_next_week",
            n_clicks=0,
            color="warning",
            size="sm",
            className="mr-2",
        ),    
    ]