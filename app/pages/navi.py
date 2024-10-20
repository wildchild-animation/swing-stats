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


from database import connect

dash.register_page(__name__, order = 100, path = "/project-nav")

def load_data():
    logging.debug("loaded default table")

    connection, cursor = connect()

    df = pd.read_sql_query(
        """
		-- Shot Tracker Data
		select distinct
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

        FROM (
		-- Shot Tracker Data
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
              entity_type.name in ('Shot')
          and
              task_status.name not in ('Omit')
          group by
              project.name, project.id, department.name, department.id, episode.name, episode.id, task_type.name, task_type.id, task_type.priority, task_status.name, task_status.id

          order by
              project.name, episode.name, task_type.priority
        ) 
        AS summary, entity shot

        inner join
            entity scene on shot.parent_id = scene.id
        inner join
            entity episode on scene.parent_id = episode.id
        inner join
            task on task.entity_id = shot.id
        inner join
            project on task.project_id = project.id
        inner join
            comment on task.id = comment.object_id
        inner join
            entity_type on shot.entity_type_id = entity_type.id
        inner join
            task_status on task.task_status_id = task_status.id
        inner join
            task_type on task.task_type_id = task_type.id
        left outer join 
            department on task_type.department_id = department.id
        left outer join
            assignations on task.id = assignations.task
        left outer join 
        	person on person.id = assignations.person
        where
        	shot.canceled = 'False'
        and
            entity_type.name in ('Shot')
        and
        	task_status.name not in ('Omit')
        and
        	summary.project_id = shot.project_id and summary.department_id = department.id and summary.episode_id = episode.id and summary.task_type_id = task_type.id and summary.task_status_id = task_status.id
        group by
        	project.name, project.id, department.name, department.id, episode.name, episode.id, task_type.name, task_type.priority, task_status.name, task_status.short_name
        order by
        	project.name, episode.name, task_type.priority

    """,
        con=connection,
    )

    ##df = df.assign(index_count=lambda x: x.id)
    ##df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))
    ## df = add_finish_column(df)
    return df

logging.debug("loading data: project details")
df = load_data()

df = df.assign(Duration = lambda x: (pd.to_datetime(x.task_end_date) - pd.to_datetime(x.task_start_date)))    

project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()

episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
artist_list = df["artists"].unique().tolist()

grid = None


def generate_table_div():
    """ Generate table rows.

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
        { 'field': 'project' },
        { 'field': 'department' },
        { 'field': 'episode' },
        { 'field': 'nb_frames' },
        { 'field': 'shot_count' },
        { 'field': 'task_type' },
        { 'field': 'priority' },
        { 'field': 'task_status' },
        { 'field': 'task_status_code' },
        { 'field': 'task_estimation' },
        { 'field': 'task_duration' },
        { 'field': 'retake_count' },
        { 'field': 'task_real_start_date' },
        { 'field': 'task_end_date' },

        { 'field': 'task_due_date' },
        { 'field': 'task_due_date' },
        { 'field': 'artists' },
    ]

    ##data_table =     dash_table.DataTable(
    ##    id='datatable-interactivity',

    #grid = dag.AgGrid(
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
                    dcc.Checklist(project_list, value=project_list, id="project_list"),                    
                    dcc.Dropdown(task_status_list, value=task_status_list, id="task_status"),
                    dcc.Dropdown(task_type_list, value=task_type_list, id="task_type"),
                    dcc.Checklist(department_list, value=department_list, id="department"),
                    dcc.Dropdown(episode_list, value=episode_list, id="episode"),                    
                ],
            ),

            html.Div(
                id="nav-datatable",
                className="datatable-interactivity",
            )
        ]
    )

#@callback(
    #Output('datatable-interactivity', 'style_data_conditional'),
    #Input('datatable-interactivity', 'selected_columns')
#)
def update_styles(selected_columns):
    return [{
        'if': { 'column_id': i },
        'background_color': '#D2F3FF'
    } for i in selected_columns]    

def layout(**kwargs):
    return html.Div(
        [
            html.H1('Projects'),
            html.Div(
                className="nav-header",
                children=[
                    generate_table_div()

                ]
            ),
            html.Div(
                className="body",
                children=[]
            ),            
        ])

@callback(
    Output('nav-datatable', 'children'),

    Input('project_list', 'value'),
    Input('department', 'value'),
    Input('episode', 'value'),
    )

def update_graphs(project, department,  episode=None, task_type=None, task_status=None, artist=None):
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
        dff = dff[dff['project'].isin(project)]

    if department:
        dff = dff[dff['department'].isin(department)]

    if episode:
        dff = dff[dff['episode'].isin(episode)]

    # Add additional filters for task_type, task_status, artist if needed

    return dash_table.DataTable(
        id='datatable-interactivity',
        columns=[
            {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
        ],
        data=dff.to_dict('records'),
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
        page_current= 0,
        page_size= 100,
    ),    

    return dff.to_dict('records')
