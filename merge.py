import os
import json
import uuid
from neo4j import GraphDatabase
from collections import defaultdict

json_path = "./arc_json"
neo4j_uri = "bolt://localhost:7687"
neo4j_username = "neo4j"
neo4j_password = "password"

def generate_uid():
    return str(uuid.uuid4())

def escape(name):
    return f"`{name}`"

driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

def create_index_for_labels(tx, labels):
    for label in labels:
        constraint_name = f"uid_constraint_{label}"
        query = f"""
            CREATE CONSTRAINT {escape(constraint_name)} IF NOT EXISTS 
            FOR (n:{escape(label)}) REQUIRE n.uid IS UNIQUE
        """
        tx.run(query)

def insert_all(tx, nodes, relationships):
    for node in nodes:
        label = escape(node['label'])
        query = f"""
            MERGE (n:{label} {{uid: $uid}})
            SET n += $props
        """
        tx.run(query, uid=node["uid"], props=node["properties"])

    for rel in relationships:
        from_label = escape(rel["from_label"])
        to_label = escape(rel["to_label"])
        rel_type = escape(rel["type"])
        query = f"""
            MATCH (a:{from_label} {{uid: $from_uid}})
            MATCH (b:{to_label} {{uid: $to_uid}})
            MERGE (a)-[r:{rel_type}]->(b)
        """
        tx.run(query, from_uid=rel["from"], to_uid=rel["to"])

def split_json(data, parent_uid=None, parent_label=None, rel_type=None, path=""):
    nodes = []
    relationships = []

    node_uid = generate_uid()
    node_label = path.split("TestCase/case/")[-1].lower() or path.split("/case/")[-1].lower() or "TestCase"

    props = {}
    if isinstance(data, dict):
        split_json_rec(data, path, nodes, relationships, node_uid, node_label, props)
    else:
        for d in data:
            split_json_rec(d, path, nodes, relationships, node_uid, node_label, props)

    node = {
        "uid": node_uid,
        "label": node_label,
        "properties": props
    }
    nodes.append(node)

    if parent_uid:
        relationships.append({
            "from": parent_uid,
            "to": node_uid,
            "type": rel_type,
            "from_label": parent_label,
            "to_label": node_label
        })

    return nodes, relationships

def split_json_rec(data, path, nodes, relationships, node_uid, node_label, props):
    for k, v in data.items():
        if isinstance(v, dict):
            child_nodes, child_rels = split_json(
                v, node_uid, node_label, f"{node_label.upper()}_TO_{k.upper()}", f"{path}/{k}"
            )
            nodes.extend(child_nodes)
            relationships.extend(child_rels)
        elif isinstance(v, list):
            if all(isinstance(item, dict) for item in v):
                for item in v:
                    child_nodes, child_rels = split_json(
                        item, node_uid, node_label, f"{node_label.upper()}_TO_{k.upper()}", f"{path}/{k}"
                    )
                    nodes.extend(child_nodes)
                    relationships.extend(child_rels)
            else:
                props[k] = v
        else:
            if k.lower() in {"id", "elementid"}:
                continue
            props[k] = v

all_nodes = []
all_relationships = []

for filename in os.listdir(json_path):
    if filename.endswith(".json"):
        file_path = os.path.join(json_path, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    nodes, relationships = split_json(data, path="TestCase")
                    all_nodes.extend(nodes)
                    all_relationships.extend(relationships)
            except Exception as e:
                print(f"[ERROR] Failed to parse {file_path}: {e}")

print(f"Parsed {len(all_nodes)} nodes and {len(all_relationships)} relationships.")

all_labels = {node["label"] for node in all_nodes}

with driver.session() as session:
    session.execute_write(create_index_for_labels, all_labels)
    session.execute_write(insert_all, all_nodes, all_relationships)

driver.close()
print("All data inserted into Neo4j successfully.")