import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

import dash
from dash import dcc, ctx, dash_table, html, Input, Output, callback
import dash_bootstrap_components as dbc
import dash_ag_grid as dag

import pandas as pd
import plotly.express as px

import pandas as pd

from database import connect

from .calcs import load_default_calcs, load_graph_calcs, filter_by_task_date
from .page_nav import get_nav_filters, get_task_filters

dash.register_page(__name__, order=25, path="/artist-data")

# Add additional filters for task_type, task_status, artist if needed
columnsDefs = [
    {"field": "project_code", "headerName": "PR"},
    {"field": "artist", "headerName": "Artist", "width": 400},
    {"field": "department", "headerName": "Dep", "width": 250},
    {"field": "task", "headerName": "Task", "width": 400},
    {
        "field": "task_type_code",
        "headerName": "Task Type",
        "width": 200,
        "cellStyle": {
            "function": "params.data.task_type_color > 0 ? {'color': params.data.task_type_color} : {'color': params.data.task_type_color}"
        },
    },
    {
        "field": "task_status_code",
        "headerName": "Task Status",
        "width": 200,
        "cellStyle": {
            "function": "params.data.task_status_color > 0 ? {'color': params.data.task_status_color} : {'color': params.data.task_status_color}"
        },
    },
    {
        "id": "status_description",
        "name": "Status",
        "deletable": True,
        "selectable": True,
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
                "field": "retake_count",
                "headerName": "Retakes",
                "filter": "agNumberColumnFilter",
                "columnGroupShow": "open",
            },
        ],
    },
    # {"field": "working_file_name", "headerName": "WF"},
    # {"field": "working_file_published_at", "headerName": "WF/Pub"},
    # {"field": "output_file_name", "headerName": "OF"},
    # {"field": "output_file_published_at", "headerName": "OF/Pub"},
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
      WITH LastFilePerTaskPerson AS (
          SELECT
              task_id,
              person_id,
              updated_at,
              name,
              ROW_NUMBER() OVER (PARTITION BY task_id, person_id ORDER BY updated_at DESC) AS rn
          FROM
              working_file
	  ),
      LastOutputFilePerTaskPerson AS (
          SELECT
              entity_id,
              person_id,
              updated_at,
              task_type_id,
              name,
              ROW_NUMBER() OVER (PARTITION BY entity_id, person_id, task_type_id ORDER BY updated_at DESC) AS rn
          FROM
              output_file
      )            
		select distinct
            project.name as project,
            project.code as project_code,

            department.name as department,

            COALESCE(person.first_name, '') ||
            CASE
                WHEN person.first_name IS NOT NULL AND person.last_name IS NOT NULL THEN ' '
                ELSE ''
            END ||
            COALESCE(person.last_name, '') as artist,
            
            CASE
            	WHEN (parent.name IS NOT NULL and gran.name IS NOT NULL) THEN gran.name
                ELSE 'ALL'
            END
            AS episode,            

            task_type.for_entity,

            CASE
            	WHEN (parent.name IS NOT NULL and gran.name IS NOT NULL) THEN gran.name || '_' || parent.name || '_' || entity.name
                ELSE entity.name
            END
            AS task,

            entity_type.name as entity_type,
            
            task_type.name as task_type,
            task_type.color as task_type_color,
            task_type.short_name task_type_code,
            
            task_status.name as task_status,
            task_status.color as task_status_color,
            task_status.short_name as task_status_code,
                                  
			((task.start_date)) AS task_start_date,
	       	((task.due_date)) AS task_due_date,

			((task.real_start_date)) AS task_real_start_date,
	       	((task.end_date)) AS task_end_date,
            
            task.estimation as task_estimation,
            task.duration as task_duration,
            task.retake_count as retake_count,

            task_type.priority,
                       
            wf.name as working_file_name,
	       	((wf.updated_at)) AS working_file_published_at,                       
                       
            outf.name as output_file_name,
	       	((outf.updated_at)) AS output_file_published_at

        from
            entity entity
        left outer join 
        	entity parent on entity.parent_id = parent.id
        left outer join
        	entity gran on parent.parent_id = gran.id

        inner join
            task on task.entity_id = entity.id
        inner join
            project on task.project_id = project.id
        inner join
            project_status on project.project_status_id = project_status.id

        inner join
            entity_type on entity.entity_type_id = entity_type.id
        inner join
            task_status on task.task_status_id = task_status.id
        inner join
            task_type on task.task_type_id = task_type.id
        left outer join 
            department on task_type.department_id = department.id

        inner join
            assignations on task.id = assignations.task
        inner join person
            on person.id = assignations.person
            
        left outer join LastFilePerTaskPerson wf on 
        	wf.task_id = task.id and wf.person_id = person.id and wf.rn = 1
            
		left outer join LastOutputFilePerTaskPerson outf on
        	outf.entity_id = entity.id and outf.person_id = person.id and outf.task_type_id = task_type.id and outf.rn = 1

        where
            project_status.name in ('Open')
        and
        	entity.canceled = 'False'
        and
        	task_status.name not in ('Omit')
            
        order by
        	artist, priority, task, task_type
              


    """,
        con=connection,
    )

    return df


logging.debug(f"loading data: {__name__}")

df = load_data()
df = load_default_calcs(df)
df = load_graph_calcs(df)

project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()

# episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
artist_list = df["artist"].unique().tolist()

grid = None


def get_nav_div():
    return html.Div(
        className="nav-header",
        children=[
            get_nav_filters(
                prefix="artist_data", 
                project_list=project_list,
                department_list=department_list,
                task_type_list=task_type_list,
                task_status_list=task_status_list,
                additional_children=get_task_filters(prefix="artist_data"),
            ),
        ],
    )


def layout(**kwargs):
    return html.Div(
        [
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H3("Artist Data", className="card-title"),
                    ]
                ),
                color="info",
                inverse=True,
                className="mb-2"
            ),     

            html.Div(
                #style={"width": "100%", "height": "200px", "border": "1px solid black"},
                style={"width": "100%", "height": "200px", "border": "none"},
                className="nav-header",
                children=[
                    get_nav_div(),
                ],
            ),
            html.Div(
                className="body",
                children=[
                    dbc.Row(
                        [
                            dbc.Col(html.Div(
                                id=f"artist_data_artist_filter",
                                children=[
                                    dcc.Dropdown(
                                        artist_list,
                                        value=artist_list,
                                        id="artist_data_artist_combo",
                                        multi=True,
                                    )
                                ],
                                #style={"width": "600px", "border": "1px solid black"},
                                style={"width": "400px", "border": "none"},
                            )),
                            dbc.Col(
                                html.Div(
                                    id="artist_data_figure",
                                    className="datatable-interactivity",
                                ),
                                #style={"width": "100%", "border": "1px solid blue"},
                                style={"width": "100%", "border": "none"},
                            )                            

                        ]
                    ),

                    dbc.Row(
                        [
                            dbc.Col(html.Div(
                                id="artist_data_datatable",
                                className="datatable-interactivity",
                                # style={"width": "100%", "height": "600px", "border": "1px solid black"},
                            )),
                        ]
                    ),

                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    id="artist_data_figure_by_artist",
                                    className="datatable-interactivity",
                                )
                            )
                        ]
                    ),                    
                ],
            ),
        ]
    )

@callback(
    Output("artist_data_artist_filter", "children"),

    Input("artist_data_project_combo", "value"),
    Input("artist_data_department_combo", "value"),
)
def update_filters(project, department):
    dff = df.copy()

    if project:
        dff = dff[dff["project"].isin(project)]

    if department:
        dff = dff[dff["department"].isin(department)]

    artist_list = dff["artist"].unique().tolist()

    return dcc.Dropdown(
        artist_list,
        value=artist_list,
        id="artist_data_artist_combo",
        multi=True,
    )


@callback(
    Output("artist_data_datatable", "children"),
    Output("artist_data_figure", "children"),    
    Output("artist_data_figure_by_artist", "children"),

    Input("artist_data_project_combo", "value"),
    Input("artist_data_department_combo", "value"),
    Input("artist_data_task_type_combo", "value"),
    Input("artist_data_task_status_combo", "value"),
    Input("artist_data_artist_combo", "value"),

    Input("artist_data_tasks_last_week", "n_clicks"),
    Input("artist_data_tasks_now", "n_clicks"),
    Input("artist_data_tasks_next_week", "n_clicks"),
)
def update_graphs(
    project,
    department,
    task_type=None,
    task_status=None,
    artist=None,

    n_clicks_last_week=False,
    n_clicks_now=False,
    n_clicks_next_week=False,
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
    dff = filter_by_task_date(dff, ctx, "artist_data")    

    if project:
        dff = dff[dff["project"].isin(project)]

    if department:
        dff = dff[dff["department"].isin(department)]

    if task_type:
        dff = dff[dff["task_type"].isin(task_type)]

    if task_status:
        dff = dff[dff["task_status"].isin(task_status)]

    if artist:
        dff = dff[dff["artist"].isin(artist)]        

    data_table = dag.AgGrid(
        id="datatable-interactivity",
        persistence=True,
        rowData=dff.to_dict("records"),
        defaultColDef=defaultColDef,
        columnDefs=columnsDefs,
        columnSize="responsiveSizeToFit",
        dashGridOptions={"animateRows": False},
        ## className="ag-theme-alpine-dark",
        style={"height": "450px", "width": "100%"},
    )

    # add chart helpers
    summary_df = dff.copy()

    summary_df = (
        summary_df.groupby(
            [
                "artist",
                "project",
                "task",
                "Start", "Finish",
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
        y="project",
        color="artist",
        hover_name="task",
        title="artist task timeline",
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

    #### fig 2 test

    fig2 = px.timeline(
        summary_df,
        x_start="Start",
        x_end="Finish",
        y="project",
        hover_name="task"
        #                   , facet_col="Dimension"
        #                   , facet_col_wrap=40
        #                   , facet_col_spacing=.99
        #                   , color_discrete_sequence=['green']*len(df)
        ,
        color_discrete_sequence=px.colors.qualitative.Prism,
        opacity=0.7
        #                   , text="Task"
        ,
        range_x=None,
        range_y=None,
        ##template="plotly_white",
        #height=1200,
        #                   , width=1500
        #,
        color="artist",
        ##title="artist task timeline",
        #                   , color=colors
    )
    fig2.update_layout(
        bargap=0.5,
        bargroupgap=0.1,
        xaxis_range=[df.Start.min(), df.Finish.max()],
        xaxis=dict(
            showgrid=True,
            rangeslider_visible=True,
            side="top",
            tickmode="array",
            dtick="M1",
            tickformat="Q%q %Y \n",
            ticklabelmode="period",
            ticks="outside",
            tickson="boundaries",
            tickwidth=0.1,
            layer="below traces",
            ticklen=20,
            tickfont=dict(family="Old Standard TT, serif", size=24, color="gray"),
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                ),
                x=0.37,
                y=-0.05,
                font=dict(family="Arial", size=14, color="darkgray"),
            ),
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            automargin=True
            #         ,anchor="free"
            ,
            ticklen=10,
            showgrid=True,
            showticklabels=True,
            tickfont=dict(family="Old Standard TT, serif", size=16, color="gray"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            title="",
            xanchor="right",
            x=1,
            font=dict(family="Arial", size=14, color="darkgray"),
        ),
        showlegend=False,        
    )
    fig2.update_traces(  # marker_color='rgb(158,202,225)'
        marker_line_color="rgb(8,48,107)", marker_line_width=1.5, opacity=0.95
    )

    # summary_df = summary_df.assign(Start = lambda x: pd.to_datetime(x.task_start_date))
    # summary_df = summary_df.assign(Finish = lambda x: pd.to_datetime(x.task_end_date))
    # summary_df = summary_df.assign(Duration = lambda x: (pd.to_datetime(x.task_end_date) - pd.to_datetime(x.task_start_date)))
    # fig = px.bar(summary_df, x="nb_frames", y="shot_count", color="task_duration", barmode="group")
    return data_table, dcc.Graph(figure=fig2), dcc.Graph(figure=fig)
