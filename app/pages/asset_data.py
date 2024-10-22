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

from .calcs import load_default_calcs
from .page_nav import get_nav_filters

dash.register_page(__name__, order=20, path="/asset-data")

# Add additional filters for task_type, task_status, artist if needed
columnsDefs = [
    {"field": "project_code", "headerName": "Project"},
    {"field": "department", "headerName": "Department"},
    #        {"field": "episode", "headerName": "Episode"},
    {"field": "entity_type", "headerName": "Type"},
    {"field": "asset_name", "headerName": "Asset"},
    {"field": "artists", "headerName": "Assigned"},
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
    {"field": "calc_estimate", "headerName": "Estimate"},
    {
        "field": "status_description",
        "headerName": "Work Status",
        "cellStyle": {
            "function": "params.data.calc_status_color ? {'color': params.data.calc_status_color} : {'color': params.data.calc_status_color}"
        },
    },
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
    {"field": "calc_task_real_start_date", "headerName": "Real Start Date"},
    {"field": "calc_task_end_date", "headerName": "End Date"},
    {"field": "calc_task_start_date", "headerName": "Start Date"},
    {"field": "calc_task_due_date", "headerName": "Due date"},
]

defaultColDef = {"editable": True, "filter": True}


def load_data():
    logging.debug("loaded default table")

    connection, cursor = connect()

    df = pd.read_sql_query(
        """
		select distinct 
            project.name as project,
            project.code as project_code, 

            department.name as department,
                       
            entity_type.name as entity_type,
            asset.name as asset_name,    
                       
            task_type.name as task_type,   
            task_type.short_name as task_type_code,
            task_type.priority,
            task_type.color as task_type_color,

            task_status.name as task_status,
            task_status.short_name as task_status_code,
            task_status.color as task_status_color,
            
            sum(task.estimation) as task_estimation,
            sum(task.duration) as task_duration,
            sum(task.retake_count) as retake_count,            

			(MIN(task.real_start_date)) AS task_real_start_date,
	       	(MAX(task.end_date)) AS task_end_date,  

			(MIN(task.start_date)) AS task_start_date,
	       	(MAX(task.due_date)) AS task_due_date,                        
                       
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
                                              
        from
            entity asset
            
        inner join 
            task on task.entity_id = asset.id
        inner join 
            project on task.project_id = project.id
        inner join
            project_status on project.project_status_id = project_status.id

        inner join 
            entity_type on asset.entity_type_id = entity_type.id
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
            project_status.name in ('Open')
        and
        	asset.canceled = 'False'
        and
        	task_status.name not in ('Omit')
        and
        	task_type.for_entity in ('Asset')
        group by
        	project.name, project.code, department.name, entity_type.name, asset.name, task_type.name, task_type.short_name, task_type.color, task_type.priority, task_status.name, task_status.short_name, task_status.color 
        order by
        	project.name, project.code, entity_type.name, asset.name, task_type.priority 
              


    """,
        con=connection,
    )

    return df


logging.debug(f"loading data: {__name__}")

df = load_data()
df = load_default_calcs(df)

project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()

# episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
##artist_list = df["artists"].unique().tolist()

grid = None


def get_nav_div():
    user_controls = [
        html.Button("Last Week", id="asset_data_tasks_last_week", n_clicks=0),
        html.Button("Now", id="asset_data_tasks_now", n_clicks=0),
        html.Button("Next Week", id="asset_data_tasks_next_week", n_clicks=0),
    ]

    return html.Div(
        className="nav-header",
        children=[
            get_nav_filters(
                "asset_data",
                project_list,
                department_list,
                task_type_list,
                task_status_list,
                additional_children=user_controls,
            ),
        ],
    )


def layout(**kwargs):
    return html.Div(
        [
            html.H1("Asset Data by Project by Department"),
            html.Div(
                style={"width": "100%", "height": "200px", "border": "1px solid black"},
                className="nav-header",
                children=[
                    get_nav_div(),
                ],
            ),
            html.Div(
                className="body",
                children=[
                    html.Div(
                        id="asset_data_datatable",
                        className="datatable-interactivity",
                        # style={"width": "100%", "height": "600px", "border": "1px solid black"},
                    ),
                ],
            ),
        ]
    )

@callback(
    Output("asset_data_datatable", "children"),
    Input("asset_data_project_combo", "value"),
    Input("asset_data_department_combo", "value"),
    Input("asset_data_task_type_combo", "value"),
    Input("asset_data_task_status_combo", "value"),

    Input("asset_data_tasks_last_week", "n_clicks"),
    Input("asset_data_tasks_now", "n_clicks"),
    Input("asset_data_tasks_next_week", "n_clicks"),    
)
def update_graphs(project, department, task_type=None, task_status=None, n_clicks_last_week = False, n_clicks_now =  False, n_clicks_next_week = False):
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
    if n_clicks_last_week:
        start = current_date_time - pd.Timedelta(days=14)
        #end = current_date_time

        logging.debug(f"Last Week: {start}")
        dff = dff[pd.to_datetime(dff["task_due_date"]) <= start]        
        #dff = dff[
        #    pd.to_datetime(dff["task_due_date"], format="mixed").between(start, end)
        #]
    elif n_clicks_now:
        start = current_date_time
        end = current_date_time + pd.Timedelta(days=14)

        logging.debug(f"Now: {start} - {end}")
        dff = dff[
            pd.to_datetime(dff["task_due_date"], format="mixed").between(start, end)
        ]
    elif n_clicks_next_week:
        #start = current_date_time
        end = current_date_time + pd.Timedelta(days=14)

        logging.debug(f"Next Week: {end}")
        #dff = dff[
        #    pd.to_datetime(dff["task_due_date"], format="mixed").between(start, end)
        #]
        dff = dff[pd.to_datetime(dff["task_due_date"]) <= end]        

    if project:
        dff = dff[dff["project"].isin(project)]

    if department:
        dff = dff[dff["department"].isin(department)]

    if task_type:
        dff = dff[dff["task_type"].isin(task_type)]

    if task_status:
        dff = dff[dff["task_status"].isin(task_status)]

    data_table = dag.AgGrid(
        id="datatable-interactivity",
        persistence=True,
        rowData=dff.to_dict("records"),
        defaultColDef=defaultColDef,
        columnDefs=columnsDefs,
        columnSize="sizeToFit",
        dashGridOptions={"animateRows": False},
        className="ag-theme-alpine-dark",
        style={"height": "600px", "width": "100%"},
    )

    return data_table
