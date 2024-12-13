from flask import g
from flask_restx import Api, fields, Resource, Namespace, marshal
import sqlite3 as sq
import os
import json, datetime

DATABASE_PATH = "database.db"

preset_api = Namespace("presets", description="Preset related operations")
model = preset_api.model("Preset", {
    "id": fields.Integer(required=True, readonly=True, description="ID of the preset"),
    "name": fields.String(required=True, readonly=False, description="The name of the preset"),
    "animation": fields.String(required=True, readonly=True, description="The name of the animation to which the preset applies"),
    "created_on": fields.DateTime(required=False, readonly=True, description="Creation date and time"),
    "json": fields.String(required=True, readonly=False, description="JSON format of the preset")
})

def get_database() -> sq.Connection:
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sq.connect(DATABASE_PATH, detect_types=sq.PARSE_DECLTYPES)
        db.row_factory = make_dicts
    return db

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

def query_db(query, args=(), one=False):
    cur = get_database().execute(query, args)
    rv = cur.fetchone() if one else cur.fetchall()  
    cur.close()
    return rv

def close_database(exception=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@preset_api.route('<int:preset_id>')
@preset_api.param('preset_id', 'The preset identifier')
@preset_api.response(404, {"success": False, "message": "Preset does not exist"})
class PresetAPI(Resource):
    init_every_request = False

    def __init__(self, model:Api):
        self.model = model

    def _get_item(self, id) -> dict | None:
        return query_db("SELECT id, name, animation, created_on, json FROM presets WHERE id=(:id)", args=dict(id=id), one=True)

    @preset_api.marshal_with(model)
    def get(self, id):
        #get a preset
        item = self._get_item(id)
        if(item is None):
            return 404, {"success": False, "message": "Preset does not exist"}
        else:
            return 200, item

    @preset_api.expect(model, validate=True)
    @preset_api.marshal_with(model)
    def put(self, id):
        #update a preset
        item = self._get_item(id)
        try:
            assert item["animation"] == preset_api.payload["animation"], "Cannot change animation of preset."
            item.update(preset_api.payload)
            item = marshal(item, model)
            query_db("UPDATE presets SET name=(:name), created_on=(:created_on), json=(:json) WHERE id=(:id)", args=item)
        except Exception as e:
            return 400, {"success": False, "message": str(e)}
        return 200, item

    @preset_api.expect(model)
    @preset_api.response(204, "Preset deleted")
    def delete(self, id):
        #delete a preset
        query_db("DELETE FROM preset WHERE id=(:id)", args=dict(id=id))
        return {"success": True}, 204

@preset_api.route("/")
class PresetListAPI(Resource):
    init_every_request = False

    def __init__(self, model):
        self.model = model

    @preset_api.marshal_list_with(model)
    def get(self):
        #get a list of all presets
        items = self.model.query.all()
        #return jsonify([item.to_json() for item in items])

    @preset_api.expect(model)
    @preset_api.marshal_with(model)
    def post(self):
        #add a new preset
        pass

def initialize():
    #verify that the database exists
    sq.register_adapter(datetime.datetime, lambda x: x.isoformat())
    sq.register_converter("DATE", lambda x: datetime.datetime.fromisoformat(x))
    sq.register_adapter(dict, lambda x: json.dumps(x, ensure_ascii=True))
    sq.register_adapter("JSON", lambda x: json.loads(x))
    if not os.path.isfile(DATABASE_PATH):
        con = sq.connect(DATABASE_PATH, detect_types=sq.PARSE_DECLTYPES)
        cur = con.cursor()
        cur.execute("CREATE TABLE presets(id INTEGER, name TEXT, animation TEXT, created_on DATE, json JSON)")
        con.commit()
        con.close()
