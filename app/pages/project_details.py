import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

import dash
from dash import dcc, dash_table, html, Input, Output, callback

import pandas as pd
import plotly.express as px

from .calcs import load_default_calcs
from .page_nav import get_nav_filters

from database import connect

dash.register_page(__name__, order=30, path="/project-details")

DATA_TABLE_COLUMNS = [
    #{
    #    "id": "id",
    #    "name": "id",
    #    "visible": False,
    #},
    { "id": "project_code", "name": "Project", "deletable": True, "selectable": True },

    { "id": "department", "name": "Department", "deletable": True, "selectable": True},
    { "id": "episode", "name": "Episode", "deletable": True, "selectable": True},

    { "id": "task_type_code", "name": "Task Type", "deletable": True, "selectable": True},
    { "id": "task_status_code", "name": "Task Status", "deletable": True, "selectable": True},

    { "id": "task_estimation", "name": "Est (D)", "deletable": True, "selectable": True},
    { "id": "task_duration", "name": "Dur (D)", "deletable": True, "selectable": True},
    { "id": "nb_frames", "name": "Frames", "deletable": True, "selectable": True},
    { "id": "shot_count", "name": "Shots", "deletable": True, "selectable": True},

    {"id": "calc_task_real_start_date", "name": "Task Real Start", "type": "datetime", "editable":False, "deletable": True, "selectable": True},
    {"id": "calc_task_end_date", "name": "Task End", "type": "datetime", "editable": False, "deletable": True, "selectable": True},
    {"id": "calc_task_start_date", "name": "Task Start", "type": "datetime", "editable":False, "deletable": True, "selectable": True},
    {"id": "calc_task_due_date", "name": "Task Due", "type": "datetime", "editable": False, "deletable": True, "selectable": True},
    
    #{"id": "Resource", "name": "Resource", "presentation": "dropdown"},
]

DATA_TABLE_STYLE = {
    "style_data_conditional": [
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(220, 220, 220)',
        }
    ],    
    "style_header": {
        "color": "white",
        "backgroundColor": "#799DBF",
        "fontWeight": "bold",
    },
    "css": [
        {
            "selector": ".Select-value",
            "rule": "padding-right: 22px",
        },  # makes space for the dropdown caret
        {"selector": ".dropdown", "rule": "position: static"},  # makes dropdown visible
    ],
}


def load_data():
    logging.debug("loaded default table")

    connection, cursor = connect()

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
              task_type.priority,
              task_type.short_name as task_type_code, 

              task_status.name as task_status,
              task_status.id as task_status_id,
              task_status.short_name as task_status_code,

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
              project.name, project.id, project.code,
              department.name, department.id, 
              episode.name, episode.id, 
              task_type.name, task_type.id, task_type.priority, task_type.short_name,
              task_status.name, task_status.id, task_status.short_name

    """,
        con=connection,
    )

    return df


logging.debug(f"loading data: {__name__}")
df = load_data()
df = load_default_calcs(df)

# Just open projects for now
## df = df[df['project_status'] == "Open"]

# df = df.assign(Start = lambda x: pd.to_datetime(x.task_start_date))
# df = df.assign(Finish = lambda x: pd.to_datetime(x.task_end_date))
# df = df.assign(Duration = lambda x: (pd.to_datetime(x.task_end_date) - pd.to_datetime(x.task_start_date)))


# set default dates


project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()
episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
#artist_list = df["artists"].unique().tolist()

grid = None


def get_nav_div():
    return html.Div(
        className="nav-header",
        children=[
            get_nav_filters("project_details", project_list, department_list, task_type_list, task_status_list, episode_list),
            html.Div(
                children = [
                ]
            )
        ],
    )

def layout(**kwargs):
    return html.Div(
        [
            html.H1("Project Details"),
            html.Div(
                className="nav-header",
                style={"height": "300px"},
                children=[get_nav_div()],
            ),
            html.Div(
                className="body",
                children=[
                    html.Div(
                        id="project_details_datatable",
                        className="datatable-interactivity",
                    ),
                    html.Div(
                        id="project_details_figure",
                        className="datatable-interactivity",
                    ),
                ],
            ),
        ]
    )

@callback(
    Output("project_details_episode_filter", "children"),

    Input("project_details_project_combo", "value"),
    Input("project_details_department_combo", "value"),
)
def update_filters(project, department):
    dff = df.copy()

    if project:
        dff = dff[dff["project"].isin(project)]

    if department:
        dff = dff[dff["department"].isin(department)]

    episode_list = dff["episode"].unique().tolist()

    return dcc.Dropdown(
        episode_list,
        value=episode_list,
        id="project_details_episode_combo",
        multi=True,
    )



@callback(
    Output("project_details_datatable", "children"),
    Output("project_details_figure", "children"),

    Input("project_details_project_combo", "value"),
    Input("project_details_department_combo", "value"),
    Input("project_details_task_type_combo", "value"),
    Input("project_details_task_status_combo", "value"),
    Input("project_details_episode_combo", "value"),    
    # Input("task_status", "value"),        
)
def update_page(
    project, department, task_type = None, task_status = None, episode = None
):
    dff = df.copy()

    if project:
        dff = dff[dff["project"].isin(project)]

    if department:
        dff = dff[dff["department"].isin(department)]

    if episode:
        dff = dff[dff["episode"].isin(episode)]

    if task_type:
        dff = dff[dff["task_type"].isin(task_type)]

    if task_status:
        dff = dff[dff["task_status"].isin(task_status)]

    if episode:
        dff = dff[dff["episode"].isin(episode)]                        

    # Add additional filters for task_type, task_status, artist if needed
    data_table = dash_table.DataTable(
        id='datatable-interactivity',
        columns=DATA_TABLE_COLUMNS,
        #columns=[
        #    {"name": i, "id": i, "deletable": True, "selectable": True}
        #    for i in df.columns
        #],
        css=DATA_TABLE_STYLE.get("css"),    
        style_data_conditional=DATA_TABLE_STYLE.get("style_data_conditional"),
        style_header=DATA_TABLE_STYLE.get("style_header"),              

        data=dff.to_dict("records"),
        editable=True,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current=0,
        page_size=20,
    )

    # Drop rows without task_start_date and task_end_date
    # summary_df = dff.dropna(
    #    subset=[
    #        "task_start_date",
    #        "task_end_date",
    #        "task_due_date",
    #       "task_real_start_date",
    #    ]
    # )

    # add chart helpers
    summary_df = dff.copy()
    summary_df = summary_df.assign(Start=lambda x: x.task_start_date)
    summary_df = summary_df.assign(Finish=lambda x: x.task_end_date)
    #
    # summary_df = summary_df.assign(Duration = lambda x: (pd.to_datetime(x.task_end_date) - pd.to_datetime(x.task_start_date)))

    summary_df = (
        summary_df.groupby(
            [
                "project",
                "episode",
                "department",
                "task_type",
                "task_status",
                pd.Grouper(key="task_start_date", freq="D"),
                pd.Grouper(key="task_end_date", freq="D"),
            ],
            ## dropna=True,
        )
        .sum(numeric_only=True)
        .reset_index()
    )
    print(summary_df)
    ## fig = px.bar(summary_df, x=df.index, y="nb_frames")

    fig = px.timeline(
        summary_df,
        x_start="task_start_date",
        x_end="task_end_date",
        y=summary_df.episode,
        color="department",
        title="",
        color_continuous_scale=[[0, "grey"], [1, "green"]],  # Red at 0%, Green at 100%
    )

    fig.update_layout(
        title_x=0.5,
        font=dict(size=16),
        yaxis=dict(
            title="",
            automargin=True,
        ),  # sorting gantt according to datatable
        xaxis=dict(title=""),
        showlegend=True,
    )

    # summary_df = summary_df.assign(Start = lambda x: pd.to_datetime(x.task_start_date))
    # summary_df = summary_df.assign(Finish = lambda x: pd.to_datetime(x.task_end_date))
    # summary_df = summary_df.assign(Duration = lambda x: (pd.to_datetime(x.task_end_date) - pd.to_datetime(x.task_start_date)))
    # fig = px.bar(summary_df, x="nb_frames", y="shot_count", color="task_duration", barmode="group")
    return data_table, dcc.Graph(figure=fig)
