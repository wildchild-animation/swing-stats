import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

import dash
from dash import dcc, dash_table, html, Input, Output, ClientsideFunction, callback

import dash_ag_grid as dag

import numpy as np
import pandas as pd


from database import connect

from .calcs import get_status_description

dash.register_page(__name__, order=15, path="/shot-data")


def load_data():
    logging.debug("loaded default table")

    connection, cursor = connect()

    df = pd.read_sql_query(
        """
          select
              project.name as project,
              project.id as project_id,
              department.id as department_id,
              department.name as department,

              episode.name as episode,
              episode.id as episode_id,

              task_type.name as task_type,
              task_type.id as task_type_id,
              task_type.priority,
              task_type.color as task_type_color,

              task_status.name as task_status,
              task_status.color as task_status_color,
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
              project.name, project.id, department.name, department.id, episode.name, episode.id, task_type.name, task_type.color, task_type.id, task_type.priority, task_status.name, task_status.color, task_status.id

          order by
              project.name, department.name, episode.name, task_type.name, task_status.name
              


    """,
        con=connection,
    )

    ##df = df.assign(index_count=lambda x: x.id)
    ##df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))
    ## df = add_finish_column(df)
    return df


logging.debug(f"loading data: {__name__}")
df = load_data()

# Just open projects for now
##df = df[df['project_status'] == "Open"]

df = df.assign(
    Duration=lambda x: (
        pd.to_datetime(x.task_end_date) - pd.to_datetime(x.task_start_date)
    )
)

## estimate is stored in minutes, convert to days
df = df.assign(
    calc_estimate=lambda x: (x.task_estimation / 60 / 8).round(2),
)

# Status Description
df["status_description"] = df.apply(lambda row: get_status_description(row), axis=1)


project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()

episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
##artist_list = df["artists"].unique().tolist()

grid = None


def get_nav_div():
    return html.Div(
        className="body",
        children=[
            html.Div(
                className="nav",
                children=[
                    html.Div(
                        className="nav-header",
                        children=[
                            dcc.Dropdown(
                                project_list,
                                value=project_list,
                                id="project_list",
                                multi=True,
                            ),
                        ],
                    ),
                    html.Div(
                        className="nav-header",
                        children=[
                            dcc.Dropdown(
                                department_list,
                                value=department_list,
                                id="department",
                                multi=True,
                            ),
                        ],
                    ),
                    html.Div(
                        className="nav-header",
                        children=[
                            dcc.Dropdown(
                                task_type_list,
                                value=task_type_list,
                                id="task_type",
                                multi=True,
                            ),
                        ],
                    ),
                    html.Div(
                        className="nav-header",
                        children=[
                            dcc.Dropdown(
                                task_status_list,
                                value=task_status_list,
                                id="task_status",
                                multi=True,
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                id="nav-datatable",
                className="datatable-interactivity",
                # style={"width": "100%", "height": "600px", "border": "1px solid black"},
            ),
        ],
    )


# @callback(
# Output('datatable-interactivity', 'style_data_conditional'),
# Input('datatable-interactivity', 'selected_columns')
# )
def update_styles(selected_columns):
    return [
        {"if": {"column_id": i}, "background_color": "#D2F3FF"}
        for i in selected_columns
    ]


def layout(**kwargs):
    return html.Div(
        [
            html.H1("Shot Data by Project by Department"),
            html.Div(className="nav-header", children=[get_nav_div()]),
            html.Div(className="body", children=[]),
        ]
    )


# Define a custom cell renderer function for task_status
def task_status_cell_renderer(params):
    return ""
    color = params.data["task_status_color"]
    return f'<div style="background-color: {color};">{params.value}</div>'


@callback(
    Output("nav-datatable", "children"),
    Input("project_list", "value"),
    Input("department", "value"),
    Input("task_type", "value"),
    Input("task_status", "value"),
)
def update_graphs(project, department, task_type=None, task_status=None):
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
        {"field": "project", "headerName": "Project"},
        {"field": "department", "headerName": "Department"},
        {"field": "episode", "headerName": "Episode"},
        {
            "field": "task_type",
            "headerName": "Task Type",
            "cellStyle": {
                "function": "params.data.task_type_color > 0 ? {'color': params.data.task_type_color} : {'color': params.data.task_type_color}"
            },
        },
        {
            "field": "task_status",
            "headerName": "Task Status",
            "cellStyle": {
                "function": "params.data.task_status_color > 0 ? {'color': params.data.task_status_color} : {'color': params.data.task_status_color}"
            },
        },
        {"field": "calc_estimate", "headerName": "Estimate"},
        {"field": "status_description", "headerName": "Status"},
        {
            "headerName": "Task",
            "children": [
                {
                    "field": "task_estimation",
                    "headerName": "Estimate",
                    "filter": "agNumberColumnFilter",
                    "columnGroupShow": "closed",
                },
                {
                    "field": "task_duration",
                    "headerName": "Duration",
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
        {"field": "task_real_start_date", "headerName": "Real Start Date"},
        {"field": "task_end_date", "headerName": "End Date"},
        {"field": "task_start_date", "headerName": "Start Date"},
        {"field": "task_due_date", "headerName": "Due date"},
    ]

    defaultColDef = {"editable": True, "filter": True}

    data_table = dag.AgGrid(
        id="datatable-interactivity",
        persistence=True,
        rowData=dff.to_dict("records"),
        defaultColDef=defaultColDef,
        columnDefs=columnsDefs,
        columnSize="sizeToFit",
        dashGridOptions={"animateRows": False},
        className="ag-theme-alpine-dark",
        style={"height": "1000px", "width": "100%"},
        ##editable=True,
        # filter_action="native",
        # sort_action="native",
        # sort_mode="multi",
        # column_selectable="single",
        ## row_selectable="multi",
        # row_deletable=True,
        # selected_columns=[],
        # selected_rows=[],
        # page_action="native",
        # page_current= 0,
        # page_size= 100,
    )

    return data_table
