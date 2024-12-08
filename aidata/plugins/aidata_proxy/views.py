from airflow.plugins_manager import AirflowPlugin
from airflow.utils.airflow_flask_app import get_airflow_app
from airflow.utils.task_group import task_group_to_dict_legacy
from airflow.www.views import AirflowBaseView, dag_to_grid
from airflow.www.app import csrf
from airflow.security import permissions
from airflow.www.views import Airflow
from airflow.configuration import AIRFLOW_CONFIG, conf
from airflow.utils import json as utils_json, timezone, yaml
from airflow.utils.session import NEW_SESSION, create_session, provide_session
from airflow.utils.dag_edges import dag_edges
from airflow.www import auth, utils as wwwutils
from airflow.models.dagrun import RUN_ID_REGEX, DagRun, DagRunType
from sqlalchemy import and_, case, desc, func, inspect, or_, select, union_all
from flask import request, Response, Blueprint, make_response
import flask.json
from flask_appbuilder import expose
import json, logging
from jinja2.utils import htmlsafe_json_dumps, pformat 


logger = logging.getLogger(__name__)

class CustomGridView(AirflowBaseView):
    route_base = "/aidata"
    
    def _handle_airflow_response(self, original_response):
        """通用的响应处理函数"""
        if isinstance(original_response, tuple) and len(original_response) == 2:
            data, headers = original_response
            try:
                # 解析原始JSON数据
                response_data = json.loads(data)
                logger.info("original_response_data: %s", original_response)
                # 创建响应对象
                response = make_response(json.dumps(response_data))
                
                # 添加CORS headers
                response.headers.update({
                    'Access-Control-Allow-Origin': 'http://localhost:3000',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Credentials': 'true'
                })
                
                # 合并原始headers和CORS headers
                logger.info("original_headers: %s", headers)
                
                logger.info("updated_response: %s", response)
                return response
            except json.JSONDecodeError:
                pass
                
        # 如果无法处理,返回原始响应
        return original_response
    
    @csrf.exempt
    @expose("/object/grid_data")
    def grid_data(self):
        """Return grid data."""
        dag_id = request.args.get("dag_id")
        dag = get_airflow_app().dag_bag.get_dag(dag_id)

        if not dag:
            return {"error": f"can't find dag {dag_id}"}, 404

        root = request.args.get("root")
        if root:
            filter_upstream = request.args.get("filter_upstream") == "true"
            filter_downstream = request.args.get("filter_downstream") == "true"
            dag = dag.partial_subset(
                task_ids_or_regex=root, include_upstream=filter_upstream, include_downstream=filter_downstream
            )

        num_runs = request.args.get("num_runs", type=int)
        if num_runs is None:
            num_runs = conf.getint("webserver", "default_dag_run_display_number")

        try:
            base_date = timezone.parse(request.args["base_date"], strict=True)
        except (KeyError, ValueError):
            base_date = dag.get_latest_logical_date() or timezone.utcnow()

        with create_session() as session:
            query = select(DagRun).where(DagRun.dag_id == dag.dag_id, DagRun.logical_date <= base_date)

        run_types = request.args.getlist("run_type")
        if run_types:
            query = query.where(DagRun.run_type.in_(run_types))

        run_states = request.args.getlist("run_state")
        if run_states:
            query = query.where(DagRun.state.in_(run_states))

        # Retrieve, sort and encode the previous DAG Runs
        dag_runs = wwwutils.sorted_dag_runs(
            query, ordering=dag.timetable.run_ordering, limit=num_runs, session=session
        )
        encoded_runs = []
        encoding_errors = []
        for dr in dag_runs:
            encoded_dr, error = wwwutils.encode_dag_run(dr, json_encoder=utils_json.WebEncoder)
            if error:
                encoding_errors.append(error)
            else:
                encoded_runs.append(encoded_dr)

        data = {
            "groups": dag_to_grid(dag, dag_runs, session),
            "dag_runs": encoded_runs,
            "ordering": dag.timetable.run_ordering,
            "errors": encoding_errors,
        }
        # avoid spaces to reduce payload size
        return (
            htmlsafe_json_dumps(data, separators=(",", ":"), dumps=flask.json.dumps),
            {"Content-Type": "application/json; charset=utf-8",
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Credentials': 'true'
             },
        )
    
    @expose("/")
    def list(self):
        """Default view."""
        return self.render_template("empty.html")

    @csrf.exempt
    @expose("/object/graph_data")
    def graph_data(self):
        """Get Graph Data."""
        dag_id = request.args.get("dag_id")
        dag = get_airflow_app().dag_bag.get_dag(dag_id)
        root = request.args.get("root")
        if root:
            filter_upstream = request.args.get("filter_upstream") == "true"
            filter_downstream = request.args.get("filter_downstream") == "true"
            dag = dag.partial_subset(
                task_ids_or_regex=root, include_upstream=filter_upstream, include_downstream=filter_downstream
            )

        nodes = task_group_to_dict_legacy(dag.task_group)
        edges = dag_edges(dag)

        data = {
            "arrange": dag.orientation,
            "nodes": nodes,
            "edges": edges,
        }
        return (
            htmlsafe_json_dumps(data, separators=(",", ":"), dumps=flask.json.dumps),
            {"Content-Type": "application/json; charset=utf-8",
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Credentials': 'true'
             },
        )

# Creating a flask blueprint
bp = Blueprint(
    "AIData",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/empty_plugin",
)

class AidataProxyPlugin(AirflowPlugin):
    name = "aidata_proxy"
    flask_blueprints = [bp]
    appbuilder_views = [{
        # "name": "AIData Grid",
        "category": "Custom",
        "category_icon": "fa-th",
        "view": CustomGridView()
    }]
