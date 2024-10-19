import logging

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

import urllib.parse

from database import connect

dash.register_page(__name__, order = 100, path = "/project-details", path_template="?<project_name>")

def layout(**kwargs):
    project_name = kwargs["project_name"] if "project_name" in kwargs else ""
    return html.Div([
        dcc.Location(id='project-details-url', refresh=False),

        html.H1('Projects Details'),
        html.Div([
            ##dcc.Graph(id="project-details-graph"),  

            dash_table.DataTable(
                id="project-details-table",
                sort_action="native",
                #columns=DATA_TABLE_COLUMNS,
                data=load_data(project_name).to_dict("records"),
                #css=DATA_TABLE_STYLE.get("css"),
                page_size=10,
                row_deletable=True,
                #style_data_conditional=DATA_TABLE_STYLE.get("style_data_conditional"),
                #style_header=DATA_TABLE_STYLE.get("style_header"),
            ),

            # My Page Init ...
            html.Div(id='project-details-page-load', style={'display': 'none'}, children='trigger'),

            # Drill down handler
            dcc.Link(id='project-details-drilldown-link', href='', children='Drill Down', style={'display': 'none'})
          
        ]),
        html.Br(),
    ])

@callback(
    Output('project-details-table', 'data'),
    Input('project-details-url', "search"))
def load_data(search: str):
    logging.debug(f"Loading default table for project_id: {search}")

    ## ToDo: search validation
    query_params = urllib.parse.parse_qs(search.lstrip('?'))
    project_name = query_params.get('project_name', [None])[0]        

    connection, cursor = connect()

    # Load data from database
    df = pd.read_sql_query(
        f"""
        select 
            project.name, project.id, project.start_date, project.end_date, 
            (
                select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id
            ) as total_tasks,
            (
                select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id and task_status.is_done
            ) as completed_tasks
        from
            project   
        where project.name = %s
        group by project.name, project.id;
        """,
        con=connection, params=[ project_name ]
    )

    # add calculated fields
    df = df.assign(index_count=lambda x: x.id)
    df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))

    # add gui helpers
    df = add_finish_column(df)    

    return df

def add_finish_column(timeline_df: pd.DataFrame):
    logging.debug("adding calcuated fields")

    """
    This function is creates 'Finish' column which is a required column for timeline chart.
    """

    if timeline_df.empty:
        return timeline_df

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

@callback(
##    Output("project-details-graph", "figure"),

    Input('project-details-url', 'search'),
    Input("project-details-table", "derived_virtual_data"),
    Input('project-details-page-load', 'children'),
)

def update_page(search, df, data):
    logging.debug(f"Search: {search}")
    logging.debug(f"User df: {df}")
    logging.debug(f"Data: {data}")


    # if user deleted all rows, return the default row:
    #if not user_datatable or len(user_datatable) == 0 or user_datatable.empty:
    #    updated_table = load_data(project_name)
    #else:
    #    updated_table = pd.DataFrame(user_datatable)

    #gantt_chart = create_gantt_chart(df)
    #return df.to_dict("records"), gantt_chart
    return None

def create_gantt_chart(df):
    logging.debug(df)

    if not df or df.empty:
        return None

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

