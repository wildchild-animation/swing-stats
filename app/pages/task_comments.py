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

from database import connect

dash.register_page(__name__, order=60, path="/task-comments")


def load_data():
    logging.debug("loaded default table")

    connection, cursor = connect()

    df = pd.read_sql_query(
        """
		select distinct 
            project.name as project,
            department.name as department,

            episode.name as episode,    
            scene.name as scene,
            shot.name as shot, 
            
            task_type.name as task_type,   
            task_type.priority as task_priority,
            task_status.name as task_status,  

            task.start_date as task_start_date,
            task.due_date as task_end_date,   
            
            comment.text as comment_text,
            comment.data as comment_data,
            comment.checklist as comment_checklist,
            
            preview_file.id as preview_file_id,

            task_type.color as task_type_color,
            task_status.color as task_status_color,            
            
            strpos(comment.text, 'Artist: ') as artpost,

            task.last_comment_date
            
        from
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
            comment on task.id = comment.object_id
        left outer join
            comment_preview_link on comment.id = comment_preview_link.comment
        left outer join
        	preview_file on comment_preview_link.preview_file = preview_file.id
        inner join 
            entity_type on shot.entity_type_id = entity_type.id
        inner join
            task_status on task.task_status_id = task_status.id
        inner join
            task_type on task.task_type_id = task_type.id
        inner join 
            department on task_type.department_id = department.id 
        inner join 
            assignations on task.id = assignations.task
        inner join person 
            on person.id = assignations.person  
        where
            project_status.name in ('Open')

           
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
# df = df[df['project_status'] == "Open"]

# nav lookups
project_list = df["project"].unique().tolist()
department_list = df["department"].unique().tolist()

episode_list = df["episode"].unique().tolist()
task_type_list = df["task_type"].unique().tolist()
task_status_list = df["task_status"].unique().tolist()
# artist_list = df["artists"].unique().tolist()
grid = None


def get_nav_div():
    return html.Div(
        className="body",
        children=[
            html.Div(
                className="nav",
                children=[
                    html.Div(
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
                        children=[
                            dcc.Dropdown(
                                task_status_list,
                                value=task_status_list,
                                id="task_status",
                                multi=True,
                            ),
                        ],
                    ),
                    html.Div(
                        id="task_comments_episode_combo",
                        children=[
                            dcc.Dropdown(
                                episode_list,
                                value=episode_list,
                                id="episode",
                                multi=True,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def layout(**kwargs):
    return html.Div(
        [
            html.H1("Comments History"),
            html.Div(
                className="nav-header",
                style={"height": "200px"},
                children=[get_nav_div()],
            ),
            html.Div(
                className="body",
                children=[
                    html.Div(
                        id="task_comments_datatable",
                        className="datatable-interactivity",
                    ),
                    html.Div(
                        id="task_comments_figure",
                        className="datatable-interactivity",
                    ),
                ],
            ),
        ]
    )

@callback(
    Output("task_comments_episode_combo", "children"),

    Input("project_list", "value"),
    Input("department", "value"),
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
        id="episode",
        multi=True,
    )


@callback(
    Output("task_comments_datatable", "children"),
    Output("task_comments_figure", "children"),
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
        id="datatable-interactivity",
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
    ## print(summary_df)
    ## fig = px.bar(summary_df, x=df.index, y="nb_frames")

    fig = px.timeline(
        summary_df,
        x_start="task_start_date",
        x_end="task_end_date",
        y="task_type",
        color="task_status",
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
