import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

import datetime

import dash
from dash import dcc, dash_table, html, Input, Output, ClientsideFunction, callback

import numpy as np
import pandas as pd
import plotly.express as px


from database import connect

dash.register_page(__name__, order=40, path="/shot-details")


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
              task_status.name as task_status,
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
              project.name, project.id, department.name, department.id, episode.name, episode.id, task_type.name, task_type.id, task_type.priority, task_status.name, task_status.id

           
    """,
        con=connection,
    )

    ##df = df.assign(index_count=lambda x: x.id)
    ##df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))
    ## df = add_finish_column(df)
    return df


logging.debug("loading data: shot details")
df = load_data()

# Just open projects for now
# df = df[df['project_status'] == "Open"]

# nav lookups
project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()

episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
#artist_list = df["artists"].unique().tolist()
grid = None


def get_nav_div():
    """Generate table rows.

    :param id: The ID of table row.
            project.name as project,
            department.name as department,

            episode.name as episode,

            SUM(DISTINCT summary.nb_frames) as nb_frames,
            SUM(DISTINCT summary.shot_count) as shot_count,

            task_type.name as task_type,
            task_type.priority,
            task_status.name as task_status,
            task_status.short_name as task_status_code,

            sum(distinct summary.task_estimation) as task_estimation,
            sum(distinct summary.task_duration) as task_duration,
            sum(distinct summary.retake_count) as retake_count,

                        TO_CHAR(MIN(task.real_start_date), 'YYYY-MM-DD') AS task_real_start_date,
                TO_CHAR(MAX(task.end_date), 'YYYY-MM-DD') AS task_end_date,

                        TO_CHAR(MIN(task.start_date), 'YYYY-MM-DD') AS task_start_date,
                TO_CHAR(MAX(task.due_date), 'YYYY-MM-DD') AS task_due_date,

            STRING_AGG(
                    DISTINCT
                COALESCE(person.first_name, '') ||
                CASE
                    WHEN person.first_name IS NOT NULL AND person.last_name IS NOT NULL THEN ' '
                    ELSE ''
                END ||
                COALESCE(person.last_name, ''),
                ', '
            ) as artists
    """

    columnDefs = [
        {"field": "project"},
        {"field": "department"},
        {"field": "episode"},
        {"field": "nb_frames"},
        {"field": "shot_count"},
        {"field": "task_type"},
        {"field": "priority"},
        {"field": "task_status"},
        {"field": "task_status_code"},
        {"field": "task_estimation"},
        {"field": "task_duration"},
        {"field": "retake_count"},
        {"field": "task_real_start_date"},
        {"field": "task_end_date"},
        {"field": "task_due_date"},
        {"field": "task_due_date"},
        {"field": "artists"},
    ]

    ##data_table =     dash_table.DataTable(
    ##    id='datatable-interactivity',

    # grid = dag.AgGrid(
    #    id="nav-datatable",
    #    style= {"height": '800px', "width": '100%'},
    #    rowData=df.to_dict("records"),
    #    columnDefs=columnDefs,
    #    #columnSize="responsiveSizeToFit",
    #    columnSize="autoSize",
    #    dashGridOptions={'pagination': True, 'pageSize': 100 }

    return html.Div(
        className="body",
        children=[
            html.Div(
                className="nav",
                children=[
                    dcc.Dropdown(project_list, value=project_list, id="project_list", multi=True),                    
                    dcc.Dropdown(task_status_list, value=task_status_list, id="task_status", multi=True),
                    dcc.Dropdown(task_type_list, value=task_type_list, id="task_type", multi=True),
                    dcc.Dropdown(department_list, value=department_list, id="department", multi=True),
                    dcc.Dropdown(episode_list, value=episode_list, id="episode", multi=True),         
                ],
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
            html.H1("Shot: Details"),
            html.Div(
                className="nav-header",
                style={"height": "200px"},
                children=[get_nav_div()],
            ),
            html.Div(
                className="body",
                children=[
                    html.Div(
                        id="shot_details_datatable",
                        className="datatable-interactivity",
                    ),
                    html.Div(
                        id="shot_details_figure",
                        className="datatable-interactivity",
                    ),
                ],
            ),
        ]
    )


@callback(
    Output("shot_details_datatable", "children"),
    Output("shot_details_figure", "children"),

    Input("project_list", "value"),
    Input("department", "value"),
    Input("episode", "value"),
    Input("task_type", "value"),
)
def update_graphs(
    project, department, episode=None, task_type=None, task_status=None, artist=None
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
        columns=[
            {"name": i, "id": i, "deletable": True, "selectable": True}
            for i in df.columns
        ],
        data=dff.to_dict("records"),
        editable=True,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=True,
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current=0,
        page_size=10,
    )

    # Drop rows without task_start_date and task_end_date
    #summary_df = dff.dropna(
    #    subset=[
    #        "task_start_date",
    #        "task_end_date",
    #        "task_due_date",
     #       "task_real_start_date",
    #    ]
   # )

    # add chart helpers
    summary_df = dff.copy()
    summary_df = summary_df.assign(Start = lambda x: x.task_start_date)
    summary_df = summary_df.assign(Finish = lambda x: x.task_end_date)    
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
