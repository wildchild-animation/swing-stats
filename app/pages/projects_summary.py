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

import pandas as pd
import plotly.express as px

from database import connect

dash.register_page(__name__, order = 1)

DATA_TABLE_COLUMNS = [
    #{
    #    "id": "id",
    #    "name": "id",
    #    "visible": False,
    #},
    {
        "id": "name",
        "name": "name",
    },
    {"id": "start_date", "name": "Start", "type": "datetime", "editable":False},
    {"id": "start_date", "name": "End", "type": "datetime", "editable": False},

    {
        "id": "total_tasks",
        "name": "total_tasks",
        "type": "numeric",
    },

    {
        "id": "completed_tasks",
        "name": "completed_tasks",
        "type": "numeric",
    }, 

    {
        "id": "perc_completed",
        "name": "perc_completed",
        "type": "numeric",
    },                   

    {
        "id": "duration",
        "name": "duration",
        "type": "numeric",
    },

    {
        "id": "project_status",
        "name": "status",
    }
    #{"id": "Resource", "name": "Resource", "presentation": "dropdown"},
]

DATA_TABLE_STYLE = {
    "style_data_conditional": [
        {"if": {"column_id": "Finish"}, "backgroundColor": "#eee"}
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
    ],
}

def get_default_table():
    logging.debug("loaded default table")

    connection, cursor = connect()

    df = pd.read_sql_query(
        """
select 
	project.name, project.id, project.start_date, project.end_date, 
    (
    	select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id
    ) as total_tasks,
    (
    	select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id and task_status.is_done
    ) as completed_tasks,
    
    project.end_date - project.start_date as duration,
    
    project_status.name as project_status
        
from
	project   
left outer join 
	project_status on project.project_status_id = project_status.id
group by project.name, project.id, project_status.name;

    """,
        con=connection,
    )

    df = df.assign(index_count=lambda x: x.id)
    df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))
    df = add_finish_column(df)
    return df


def add_finish_column(timeline_df: pd.DataFrame):
    logging.debug("adding calcuated fields")

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
    logging.debug(df)

    fig = px.timeline(
        df,
        x_start="start_date",
        x_end="end_date",
        y=df.name,
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


layout = html.Div([
    html.H1('Projects'),
    html.Div([
        dcc.Graph(id="gantt-graph"),  

        dash_table.DataTable(
            id="user-datatable",
            sort_action="native",
            columns=DATA_TABLE_COLUMNS,
            data=get_default_table().to_dict("records"),
            css=DATA_TABLE_STYLE.get("css"),
            page_size=10,
            row_deletable=True,
            style_data_conditional=DATA_TABLE_STYLE.get("style_data_conditional"),
            style_header=DATA_TABLE_STYLE.get("style_header"),
        ),

        # My Page Init ...
        html.Div(id='page-load-trigger', style={'display': 'none'}, children='trigger'),

        # Drill down handler
        dcc.Link(id='drilldown-link', href='', children='Drill Down', style={'display': 'none'})
      
    ]),
    html.Br(),
])
@callback(
    Output("user-datatable", "data"),
    Output("gantt-graph", "figure"),
        
    Input("user-datatable", "derived_virtual_data"),
    Input('page-load-trigger', 'children'),
)

def update_page(user_datatable, data):

    logging.debug(f"User datatable: {user_datatable}")
    logging.debug(f"Data: {data}")

    # if user deleted all rows, return the default row:
    if not user_datatable:
        updated_table = pd.DataFrame()

    else:
        updated_table = pd.DataFrame(user_datatable)

    updated_table_as_df = add_finish_column(updated_table)
    gantt_chart = create_gantt_chart(updated_table_as_df)

    return updated_table_as_df.to_dict("records"), gantt_chart

@callback(
    Output('drilldown-link', 'href'),
    Output('drilldown-link', 'style'),
    ##Output('drill-down', 'project-details-content.children'),
    Input('gantt-graph', 'clickData')
)
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

