from flask import g, jsonify, render_template
from flask_restx import Api, fields, Resource, Namespace, marshal
import sqlite3 as sq
import os
import json, datetime
from animations.animations import AnimData
import queue, threading
import html
from typing import Tuple, Any

PRESET_TEMPLATE = "presets.html"
DATABASE_PATH = "database.db"

preset_api = Namespace("presets", description="Preset related operations", path="/api/presets")
model = preset_api.model("Preset", {
    "id": fields.Integer(required=True, readonly=True, description="ID of the preset"),
    "name": fields.String(required=True, readonly=False, description="The name of the preset"),
    "animation": fields.String(required=True, readonly=True, description="The name of the animation to which the preset applies"),
    "created_on": fields.DateTime(required=False, readonly=True, description="Creation date and time"),
    "json": fields.String(required=True, readonly=False, description="JSON format of the preset")
})
animdata = AnimData()

def get_database() -> 'ThreadedDatabaseHandler':
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = ThreadedDatabaseHandler(DATABASE_PATH)
    return db

def close(exception=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@preset_api.route('/create', methods=['POST'])
@preset_api.route('/<int:preset_id>', methods=['GET', 'PUT', 'DELETE'])
@preset_api.param('preset_id', 'The preset identifier')
@preset_api.response(404, {"success": False, "message": "Preset does not exist"})
class PresetAPI(Resource):
    init_every_request = False

    def __init__(self, model:Api):
        self.model = model

    def _get_item(self, id) -> dict | None:
        res, _ = get_database().execute("SELECT id, name, animation, created_on, json FROM presets WHERE id=(:id)", args=dict(id=id), one=True)
        if res is not None:
            return res
        return None

    @preset_api.marshal_with(model)
    def get(self, id):
        #get a preset
        item = self._get_item(id)
        if(item is None):
            return {"success": False, "message": "Preset does not exist"}, 404
        else:
            return item, 200
        
    @preset_api.expect(model, validate=True)
    @preset_api.marshal_with(model)
    def put(self, id):
        #update a preset
        item = self._get_item(id)
        if item is None:
            return {"success": False, "message": "Preset does not exist"}, 404
        try:
            assert item["animation"] == preset_api.payload["animation"], "Cannot change animation of preset."
            item.update(preset_api.payload)
            item = marshal(item, model)
            get_database().execute("UPDATE presets SET name=(:name), created_on=(:created_on), json=(:json) WHERE id=(:id)", args=item, commit=True)
        except Exception as e:
            return {"success": False, "message": str(e)}, 400
        return item, 200

    @preset_api.response(204, "Preset deleted")
    def delete(self, id):
        #delete a preset
        get_database().execute("DELETE FROM preset WHERE id=(:id)", args=dict(id=id), commit=True)
        return {"success": True}, 204
    
    #@preset_api.expect(model, validate=True)
    #@preset_api.marshal_with(model)
    def post(self):
        #create a new preset
        payload = preset_api.payload
        #item = marshal(preset_api.payload, model)
        payload["created_on"] = datetime.datetime.now()
        if payload.get("animation", None) is None:
            return {"success": False, "message": "Animation not specified"}, 400
        elif payload.get("json", None) is None:
            return {"success": False, "message": "JSON not specified"}, 400
        elif payload.get("name", None) is None:
            return {"success": False, "message": "Name not specified"}, 400
        params = payload["json"]
        if type(params) is str:
            params = json.loads(params)
        if "name" in params:
            del params["name"]
        #verify that the paramters match the animation
        anim = animdata.get(payload["animation"])
        if anim is None:
            return "Invalid animation", 400
        settings = anim.settings
        if not all([param in params for param in settings]):
            return "Missing parameters", 400
        if not all([param in settings for param in params]):
            return "Invalid parameters", 400
        get_database().execute("INSERT INTO presets (name, animation, created_on, json) VALUES (:name, :animation, :created_on, :json)",
                    args=payload, commit=True)
        res = {"success": True, "name": payload["name"], "animation": payload["animation"], "json": params}
        return res, 201

@preset_api.route("/")
@preset_api.route("/animation/<string:animation>")
class PresetListAPI(Resource):
    init_every_request = False

    def __init__(self, model):
        self.model = model

    #@preset_api.marshal_list_with(model)
    def get(self, animation=None):
        #get a list of all presets
        if animation is None:
            items, _ = get_database().execute("SELECT id, name, animation, created_on, json FROM presets")
        else:
            items, _ = get_database().execute("SELECT id, name, animation, created_on, json FROM presets WHERE animation=(:animation)", args=dict(animation=animation))
        if items is None:
            return {"success": False, "message": "No presets found"}, 404
        return jsonify([item for item in items])

def render_preset_template():
    #create preset table
    items, _ = get_database().execute("SELECT id, name, animation, created_on, json FROM presets")
    anims = {}
    for item in items:  # type: ignore
        if item["animation"] not in anims:
            anims[item["animation"]] = []
        anims[item["animation"]].append(item)
    #sort animations by name
    anims = dict(sorted(anims.items(), key=lambda x: x[0]))
    
    tables = []
    for anim in anims:
        sanitized_name = html.escape(anim.replace(" ", "-"))
        table = f"<div class='col'><h3 style='text-align: center' class='preset_heading' id='heading_{sanitized_name}'>{html.escape(anim)}</h3>"
        table += f"<ul id='list_{sanitized_name:s}' class='preset_list'>\n"
        for preset in anims[anim]:
            sanitized_preset_name = html.escape(preset["name"])
            table += f"<li onclick='window.location.href=\"home?animation={html.escape(anim):s}&preset={preset['id']:d}\";'><span class='preset_name'>{sanitized_preset_name:s}</span></li>\n"
        table += "</ul></div>\n"
        tables.append(table)
    return render_template(PRESET_TEMPLATE, table_presets="\n".join(tables))

#ensure that this is threadsafe
class ThreadedDatabaseHandler:
    #make it a singleton
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ThreadedDatabaseHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_file):
        self.db_file = db_file
        sq.register_adapter(datetime.datetime, lambda x: x.strftime("%Y-%m-%d %H:%M:%S"))
        sq.register_converter("DATE", lambda x: datetime.datetime.fromisoformat(x.decode()))
        sq.register_adapter(dict, lambda x: json.dumps(x, ensure_ascii=True))
        sq.register_adapter("JSON", lambda x: json.loads(x))  # type: ignore
        if not os.path.isfile(DATABASE_PATH):
            print("!!! Creating database !!!")
            con = sq.connect(DATABASE_PATH, detect_types=sq.PARSE_DECLTYPES)
            cur = con.cursor()
            cur.execute("CREATE TABLE presets(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, animation TEXT, created_on DATE, json JSON)")
            con.commit()
            con.close()
            self.connection = None
        self.query_queue = queue.Queue()
        self.db_thread = threading.Thread(target=self._worker)
        self.db_thread.daemon = True
        self.db_thread.start()

    def make_dicts(self, cursor, row):
        return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

    def _worker(self):
        con = sq.connect(self.db_file, detect_types=sq.PARSE_DECLTYPES)
        con.row_factory = self.make_dicts
        while True:
            query, args, one, commit, result_queue = self.query_queue.get()
            if query is None:
                break
            cur = con.cursor()
            args = args or ()
            cur.execute(query, args)
            if commit:
                con.commit()
            if one:
                result_queue.put((cur.fetchone(), 1))
            else:
                result_queue.put((cur.fetchall(), cur.rowcount))
            cur.close()
        con.close()
    
    def execute(self, query: str, args: sq._Parameters | None = None, one: bool = False, commit: bool = False) -> Tuple[Any | None, int]:
        args = args or ()
        res_queue = queue.Queue(1)
        self.query_queue.put((query, args, one, commit, res_queue))
        res, count = res_queue.get()
        return (None if res is None or len(res)==0 else res), count

    def __del__(self):
        self.close()
        ThreadedDatabaseHandler._instance = None
    
    def close(self):
        print("Closing ThreadedDatabaseHandler")
        self.query_queue.put((None,None,None, None, None))
        self.db_thread.join()