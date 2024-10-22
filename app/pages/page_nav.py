from dash import dcc, html


def get_nav_filters(
    prefix: str,
    project_list=None,
    department_list=None,
    task_type_list=None,
    task_status_list=None,
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
            html.Div(
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
