import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, html, dcc, Input, Output, dash_table, ctx
import plotly.express as px

from database import connect

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
        {"selector": ".dropdown", "rule": "position: static"},  # makes dropdown visible
    ],
}

# Default new row for datatable
new_task_line = {
    "Task": "",
    "Start": "2016-01-01",
    "Duration": 0,
    "Resource": "A",
    "Finish": "2016-01-01",
}
df_new_task_line = pd.DataFrame(new_task_line, index=[0])


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

    logging.debug(df)

    df = df.assign(index_count=lambda x: x.id)
    df = df.assign(perc_completed=lambda x: (x.completed_tasks / x.total_tasks * 100).round(2))

    logging.debug(df)
    df = add_finish_column(df)
    logging.debug(df)
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


app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.SPACELAB],
    suppress_callback_exceptions=False,
    prevent_initial_callbacks=False,
)

app.layout = dbc.Container(
    [
        html.H1("Project Time Line", className="bg-primary text-white p-1 text-center"),
        dbc.Button("Add task", n_clicks=0, id="add-row-btn", size="sm"),
        dash_table.DataTable(
            id="user-datatable",
            sort_action="native",
            columns=DATA_TABLE_COLUMNS,
            data=get_default_table().to_dict("records"),
            #editable=True,
            #dropdown={
            #    "Resource": {
            #        "clearable": False,
            #        "options": [{"label": i, "value": i} for i in ["A", "B", "C", "D"]],
            #    },
            #},
            css=DATA_TABLE_STYLE.get("css"),
            page_size=10,
            row_deletable=True,
            style_data_conditional=DATA_TABLE_STYLE.get("style_data_conditional"),
            style_header=DATA_TABLE_STYLE.get("style_header"),
        ),
        dcc.Graph(id="gantt-graph"),
    ],
    fluid=True,
)


def create_gantt_chart(updated_table_as_df):
    logging.debug(updated_table_as_df)

    gantt_fig = px.timeline(
        updated_table_as_df,
        x_start="start_date",
        x_end="end_date",
        y=updated_table_as_df.name,
        color="perc_completed",
        title="Project Plan Gantt Chart",
        color_continuous_scale=[[0, "grey"], [1, "green"]],  # Red at 0%, Green at 100%
    )

    gantt_fig.update_layout(
        title_x=0.5,
        font=dict(size=16),
        yaxis=dict(
            title="Project",
            automargin=True,
        ),  # sorting gantt according to datatable
        xaxis=dict(title=""),

    )

    #gantt_fig.update_layout(
    #    title_x=0.5,
    #    font=dict(size=16),
    #    yaxis=dict(
    #        title="Task",
    #        automargin=True,
    #        autorange="reversed",
    #        categoryorder="array",
    #        categoryarray=updated_table_as_df["Task"],
    #    ),  # sorting gantt according to datatable
    #    xaxis=dict(title=""),
    #)
    gantt_fig.update_traces(width=0.7)

    return gantt_fig


@app.callback(
    Output("user-datatable", "data"),
    Output("gantt-graph", "figure"),
    Input("user-datatable", "derived_virtual_data"),
    Input("add-row-btn", "n_clicks"),
)
def update_table_and_figure(user_datatable: None or list, _):

    # if user deleted all rows, return the default row:
    if not user_datatable:
        updated_table = df_new_task_line

    # if button clicked, then add a row
    elif ctx.triggered_id == "add-row-btn":
        updated_table = pd.concat([pd.DataFrame(user_datatable), df_new_task_line])

    else:
        updated_table = pd.DataFrame(user_datatable)

    updated_table_as_df = add_finish_column(updated_table)
    gantt_chart = create_gantt_chart(updated_table_as_df)

    return updated_table_as_df.to_dict("records"), gantt_chart


if __name__ == "__main__":
    app.run_server(debug=False)
