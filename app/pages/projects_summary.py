import logging
import urllib

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
import dash
from dash import html, dcc, callback, Input, Output, html, dcc, Input, Output, dash_table

import dash_ag_grid as dag

import pandas as pd
import plotly.express as px

from database import connect

dash.register_page(__name__, order = 10)

def load_data():
    logging.debug("loaded default table")

    connection, cursor = connect()

    df = pd.read_sql_query(
        """
select 
	project.name as project, project_status.name as project_status, project.id, project.start_date, project.end_date, 
    (
    	select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id
    ) as total_tasks,
    (
    	select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id and task_status.is_done
    ) as completed_tasks,
    
    project.end_date - project.start_date as duration
        
from
	project   
left outer join 
	project_status on project.project_status_id = project_status.id
where
    project_status.name in ('Open')
group by project.name, project.id, project_status.name;

    """,
        con=connection,
    )

    # add caculated fields
    df = df.assign(index_count=lambda x: x.id)
    df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))

    # add chart helpers
    df = df.assign(Start = lambda x: x.start_date)
    df = df.assign(Finish = lambda x: x.end_date)

    df = df.assign(Duration = lambda x: (pd.to_datetime(x.end_date) - pd.to_datetime(x.start_date)))    
    return df

def add_finish_column(timeline_df: pd.DataFrame):
    logging.debug("adding calculated fields")

    """
    This function is creates 'Finish' column which is a required column for timeline chart.
    """
    timeline_df["Start"] = pd.to_datetime(timeline_df["start_date"])
    timeline_df["Duration"] = pd.to_datetime(timeline_df["end_date"]) - pd.to_datetime(
        timeline_df["start_date"]
    )

    # timeline_df["Finish"] = timeline_df["Start"] + pd.to_timedelta(
    #    timeline_df["Duration"], unit="D"
    # )
    timeline_df["Start"] = pd.to_datetime(timeline_df["start_date"]).dt.date
    timeline_df["Finish"] = pd.to_datetime(timeline_df["end_date"]).dt.date
    return timeline_df

def create_gantt_chart(df):
    #logging.debug("creating gantt chart")
    #logging.debug(df)

    if df.empty:
        return html.Div("No data to display")

    fig = px.timeline(
        df,
        x_start="start_date",
        x_end="end_date",
        y=df.project,
        color="perc_completed",
        title="",
        color_continuous_scale=[[0, "grey"], [1, "green"]],  # Red at 0%, Green at 100%
    )

    #fig.add_trace(px.scatter(
    #    name="Raw Data",
    #    mode="markers+lines", x=df["start_date"], y=df["perc_completed"],
    #    marker_symbol="star"
    #))    

    fig.update_layout(
        title_x=0.5,
        font=dict(size=16),
        yaxis=dict(
            title="",
            automargin=True,
        ),  # sorting gantt according to datatable
        xaxis=dict(title=""),
        showlegend=False,        

    )

    return fig

logging.debug("loading data: project summary")
df = load_data()

# Just open projects for now
## df = df[df['project_status'] == "Open"]

def layout(**kwargs):
    return html.Div(
        [
            html.H1("Running Projects"),
            html.Div(
                className="nav-header",
            ),
            html.Div(
                className="body",
                children=[
                    html.Div(
                        id="project_summary_datatable",
                        className="datatable-interactivity",
                    ),
                    html.Div(
                        id="project_summary_figure",
                        className="datatable-interactivity",
                    ),
                ],
            ),
        ]
    )
@callback(
    Output("project_summary_datatable", "children"),
    Output("project_summary_figure", "children"),

    Input("project_summary_figure", "n_clicks"),
)

def update_page(n_clicks):

    ##dff = df.copy()
    ##logging.debug(f"User datatable: {data}")
    # if user deleted all rows, return the default row:

    columnsDefs = [
        {"field": "project", "headerName": "Project"},
        {"field": "start_date", "headerName": "Start"},
        {"field": "end_date", "headerName": "End"},
        {"field": "duration", "headerName": "Production Days"},
        {"field": "total_tasks", "headerName": "Total Tasks"},
        {"field": "completed_tasks", "headerName": "Completed Tasks"},
        {"field": "perc_completed", "headerName": "%"},

    ]

    defaultColDef = {"editable": True, "filter": True}

    data_table = dag.AgGrid(
            id="datatable-interactivity",
            rowData=df.to_dict("records"),
            defaultColDef=defaultColDef,
            columnDefs=columnsDefs,
            columnSize="auto",
            dashGridOptions={"animateRows": False},
            className="ag-theme-alpine-dark",            
            # editable=True,
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
        ),

    ### updated_table_as_df = add_finish_column(updated_table)
    figure = create_gantt_chart(df)

    return data_table, dcc.Graph(figure=figure)

#@callback(
#    Output('drilldown-link', 'href'),
#    Output('drilldown-link', 'style'),#

    #Input('gantt-graph', 'clickData')
#)
def drilldown(event):
    logging.debug(f"Drilldown clicked: {event}")

    if event:
        if 'points' not in event:
            logging.debug("No points in clickData")
            return
        
        points = event['points']
        if not points or len(points) == 0:
            logging.debug("No points in clickData")
            return
        
        click_data = points[0]
        project_name = click_data["label"]

        logging.debug(f"Drilldown clicked: {project_name}")
        query_params = urllib.parse.urlencode({'project_name': project_name})

        logging.debug(f"Navigate to project details: {query_params}")   
        return f'/project-details?{query_params}', {'display': 'block'}
          
    
    return '', {'display': 'none'}

