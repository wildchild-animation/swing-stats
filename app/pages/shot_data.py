import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

import dash
from dash import ctx, dcc, dash_table, html, Input, Output, ClientsideFunction, callback
import dash_bootstrap_components as dbc

import dash_ag_grid as dag

import numpy as np
import pandas as pd


from database import connect, close

from .calcs import load_default_calcs, filter_by_task_date
from .page_nav import get_nav_filters, get_task_filters


dash.register_page(__name__, order=15, path="/shot-data")


def load_data():
    logging.debug("loaded default table")

    connection, cursor = connect()
    try:
        df = pd.read_sql_query(
            """
            select
                project.name as project,
                project.code as project_code,
                project.id as project_id,
                department.id as department_id,
                department.name as department,

                episode.name as episode,
                episode.id as episode_id,

                task_type.name as task_type,
                task_type.id as task_type_id,
                task_type.short_name as task_type_code,

                task_type.priority,
                task_type.color as task_type_color,

                task_status.name as task_status,
                task_status.color as task_status_color,
                task_status.short_name as task_status_code,

                task_status.id as task_status_id,

                sum(task.estimation) as task_estimation,
                sum(task.duration) as task_duration,
                sum(task.retake_count) as retake_count,
                

                (MIN(task.real_start_date)) AS task_real_start_date,
                (MAX(task.end_date)) AS task_end_date,

                (MIN(task.start_date)) AS task_start_date,
                (MAX(task.due_date)) AS task_due_date,              

                SUM(DISTINCT CASE
                        WHEN shot.name = 'sh000' THEN 0
                        ELSE shot.nb_frames
                END) AS nb_frames,

                COUNT(CASE
                        WHEN shot.name = 'sh000' THEN 0
                        ELSE 1
                END) AS shot_count

            FROM
                entity shot
            inner join
                entity scene on shot.parent_id = scene.id
            inner join
                entity episode on scene.parent_id = episode.id
            inner join
                task on task.entity_id = shot.id
            inner join
                project on task.project_id = project.id
            inner join
                project_status on project.project_status_id = project_status.id
            inner join
                entity_type on shot.entity_type_id = entity_type.id
            inner join
                task_status on task.task_status_id = task_status.id
            inner join
                task_type on task.task_type_id = task_type.id
            left outer join 
                department on task_type.department_id = department.id
            where
                shot.canceled = 'False'
            and
                project_status.name in ('Open')
            and
                entity_type.name in ('Shot')
            and
                task_status.name not in ('Omit')
            group by
                project.name, project.id, project_code, 
                department.name, department.id, 
                episode.name, episode.id, 
                task_type.name, task_type.color, task_type.id, task_type.short_name, task_type.priority, 
                task_status.name, task_status.color, task_status.id, task_status.short_name

            order by
                project.code, department.name, episode.name, task_type.name, task_status.name
                


        """,
            con=connection,
        )

        ##df = df.assign(index_count=lambda x: x.id)
        ##df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))
        ## df = add_finish_column(df)
        return df
    finally:
        close(connection)


logging.debug(f"loading data: {__name__}")


df = load_data()
df = load_default_calcs(df)

project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()

episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
##artist_list = df["artists"].unique().tolist()

grid = None


def get_nav_div():
    return html.Div(
        className="nav-header",
        children=[
            get_nav_filters(
                "shot_data",
                project_list=project_list,
                department_list=department_list,
                task_type_list=task_type_list,
                task_status_list=task_status_list,

                additional_children=get_task_filters("shot_data"),
            ),
        ],
    )


def layout(**kwargs):
    return html.Div(
        [
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H3("Shot Data", className="card-title"),
                    ]
                ),
                color="info",
                inverse=True,
                className="mb-2",
            ),
            html.Div(
                style={"width": "100%", "height": "200px", "border": "1px solid black"},
                className="nav-header",
                children=[get_nav_div()],
            ),
            html.Div(children=[]),
            html.Div(
                className="body",
                children=[
                    html.Div(
                        id="shot_data_datatable",
                        className="datatable-interactivity",
                    ),
                ],
            ),
        ]
    )


@callback(
    Output("shot_data_datatable", "children"),

    Input("shot_data_project_combo", "value"),
    Input("shot_data_department_combo", "value"),
    Input("shot_data_task_type_combo", "value"),
    Input("shot_data_task_status_combo", "value"),

    Input("shot_data_tasks_reset", "n_clicks"),
    Input("shot_data_tasks_last_week", "n_clicks"),
    Input("shot_data_tasks_now", "n_clicks"),
    Input("shot_data_tasks_next_week", "n_clicks"),
)
def update_page(
    project,
    department,
    task_type=None,
    task_status=None,
    n_clicks_last_week=False,
    n_clicks_now=False,
    n_clicks_next_week=False,
    n_clicks_reset=False,
):
    # When the table is first rendered, `derived_virtual_data` and
    # `derived_virtual_selected_rows` will be `None`. This is due to an
    # idiosyncrasy in Dash (unsupplied properties are always None and Dash
    # calls the dependent callbacks when the component is first rendered).
    # So, if `rows` is `None`, then the component was just rendered
    # and its value will be the same as the component's dataframe.
    # Instead of setting `None` in here, you could also set
    # `derived_virtual_data=df.to_rows('dict')` when you initialize
    # the component.

    dff = df.copy()

    current_date_time = pd.Timestamp.now()
    logging.debug(f"Current Date Time: {current_date_time}")

    dff = df.copy()
    dff = filter_by_task_date(dff, ctx, "shot_data")

    if project:
        dff = dff[dff["project"].isin(project)]

    if department:
        dff = dff[dff["department"].isin(department)]

    if task_type:
        dff = dff[dff["task_type"].isin(task_type)]

    if task_status:
        dff = dff[dff["task_status"].isin(task_status)]

    # Add additional filters for task_type, task_status, artist if needed

    columnsDefs = [
        {"field": "project_code", "headerName": "Project"},
        {"field": "department", "headerName": "Department"},
        {"field": "episode", "headerName": "Episode"},
        {
            "field": "task_type_code",
            "headerName": "Task Type",
            "cellStyle": {
                "function": "params.data.task_type_color > 0 ? {'color': params.data.task_type_color} : {'color': params.data.task_type_color}"
            },
        },
        {
            "field": "task_status_code",
            "headerName": "Task Status",
            "cellStyle": {
                "function": "params.data.task_status_color > 0 ? {'color': params.data.task_status_color} : {'color': params.data.task_status_color}"
            },
        },
        {"field": "calc_estimate", "headerName": "Estimate (D)"},
        {
            "field": "status_description",
            "headerName": "Work Status",
            "cellStyle": {
                "function": "params.data.calc_status_color ? {'color': params.data.calc_status_color} : {'color': params.data.calc_status_color}"
            },
        },
        {
            "headerName": "Task",
            "columnGroupShow": "closed",
            "children": [
                {
                    "field": "calc_estimation",
                    "headerName": "Estimate (D)",
                    "filter": "agNumberColumnFilter",
                    "columnGroupShow": "closed",
                },
                {
                    "field": "calc_duration",
                    "headerName": "Duration (D)",
                    "filter": "agNumberColumnFilter",
                    "columnGroupShow": "closed",
                },
                {
                    "field": "nb_frames",
                    "headerName": "Frames",
                    "filter": "agNumberColumnFilter",
                    "columnGroupShow": "open",
                },
                {
                    "field": "shot_count",
                    "headerName": "Shots",
                    "filter": "agNumberColumnFilter",
                    "columnGroupShow": "closed",
                },
            ],
        },
        {"field": "calc_task_real_start_date", "headerName": "Work Start"},
        {"field": "calc_task_end_date", "headerName": "Work End"},
        {"field": "calc_task_start_date", "headerName": "Task Start"},
        {"field": "calc_task_due_date", "headerName": "Task Due"},
    ]

    defaultColDef = {"editable": True, "filter": True}

    data_table = dag.AgGrid(
        id="datatable-interactivity",
        persistence=True,
        rowData=dff.to_dict("records"),
        defaultColDef=defaultColDef,
        columnDefs=columnsDefs,
        columnSize="responsiveSizeToFit",
        style={"height": "600px", "width": "100%"},
        className="ag-theme-alpine-dark",
    )

    return data_table
