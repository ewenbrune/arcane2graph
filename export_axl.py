from neo4j import GraphDatabase
import os
import json

class JSONToNeo4jVisitor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.counter = 0

    def close(self):
        self.driver.close()

    def create_module(self, module_data):
        with self.driver.session() as session:
            result = session.run(
                f"CREATE (m:{str(module_data["Name"])}"+"{name: $name, type: $type, interfaces: $interfaces}) RETURN id(m)",
                {"name": module_data["Name"], "type": module_data["Type"], "interfaces": module_data["Interface"]}
            )
            return result.single()[0]  # Internal node id of the Module

    def create_option(self, session, parent_id, option_data):
        # Create node
        result = session.run(
            """
            MATCH (p) WHERE id(p) = $parent_id
            CREATE (o:Option {
                name: $name,
                type: $type,
                hasDefault: $hasDefault,
                defaultValue: $defaultValue,
                hasMinOccursAttribute: $hasMinOccursAttribute,
                minOccurs: $minOccurs,
                hasMaxOccursAttribute: $hasMaxOccursAttribute,
                maxOccurs: $maxOccurs,
                isOptional: $isOptional,
                fullName: $fullName,
                id: $id
            })
            CREATE (p)-[:HAS_OPTION]->(o)
            RETURN id(o)
            """,
            {
                "parent_id": parent_id,
                "name": option_data["Name"],
                "type": option_data["Type"],
                "hasDefault": option_data["HasDefault"],
                "defaultValue": option_data["DefaultValue"],
                "hasMinOccursAttribute": option_data["HasMinOccursAttribute"],
                "minOccurs": option_data["MinOccurs"],
                "hasMaxOccursAttribute": option_data["HasMaxOccursAttribute"],
                "maxOccurs": option_data["MaxOccurs"],
                "isOptional": option_data["IsOptional"],
                "fullName": option_data["FullName"],
                "id": option_data["Id"]
            }
        )
        return result.single()[0]  # Internal node id of the Option

    def visit_option(self, session, parent_id, option_data):
        option_id = self.create_option(session, parent_id, option_data)
        for sub_option in option_data.get("Options", []):
            self.visit_option(session, option_id, sub_option)

    def process(self, data):
        with self.driver.session() as session:
            module_id = self.create_module(data)
            for option in data.get("Options", []):
                self.visit_option(session, module_id, option)


input_dir = "./axl_json"

for dirpath,_,files in os.walk(input_dir):
    for filename in files:
        if filename.endswith(".json"):
            json_path = os.path.join(dirpath, filename)

            with open(json_path) as f:
                data = json.load(f)
            visitor = JSONToNeo4jVisitor("bolt://localhost:7687", "neo4j", "password")
            visitor.process(data)
            visitor.close()



def link_interfaces(tx):
    query = """
    MATCH (m)
    WHERE m.interfaces IS NOT NULL
    UNWIND m.interfaces AS interface_name
    MATCH (o:Option)
    WHERE interface_name = o.type
    MERGE (m)-[:IMPLEMENTS]->(o)
    """
    tx.run(query)

def create_specifies_option_relationships(tx):
    result = tx.run("MATCH (o:Option) RETURN o.fullName AS label, id(o) AS oid")
    
    for record in result:
        label = record["label"]
        oid = record["oid"]
        
        dynamic_cypher = f"""
        MATCH (n:`{label}`), (o:Option)
        WHERE id(o) = $oid
        MERGE (o)-[:SPECIFIES]->(n)
        """
        
        tx.run(dynamic_cypher, oid=oid)

def create_specifies_service_relationships(tx):
    result = tx.run("MATCH (n) WHERE n.`@name` IS NOT NULL RETURN n.`@name` AS name, id(n) as oid")
    
    for record in result:
        name = record["name"]
        oid = record["oid"]
        
        dynamic_cypher = f"""
        MATCH (n:`{name}`), (o)
        WHERE id(o) = $oid
        MERGE (n)-[:SPECIFIES]->(o)
        """
        
        tx.run(dynamic_cypher, oid=oid)

def create_specifies_module_relationships(tx):
    result = tx.run("MATCH (n) RETURN id(n) as oid, labels(n)[0] AS name")
    
    for record in result:
        name = record["name"]
        name = [word[0].upper() + word[1:] for word in name.split()][0]
        oid = record["oid"]
        
        print(name)
        dynamic_cypher = f"""
        MATCH (n:`{name}`), (o)
        WHERE id(o) = $oid AND n.type = 'module' AND id(n) <> $oid
        MERGE (n)-[:SPECIFIES]->(o)
        """
        
        tx.run(dynamic_cypher, oid=oid)

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    session.execute_write(link_interfaces)
    session.execute_write(create_specifies_option_relationships)
    session.execute_write(create_specifies_service_relationships)
    session.execute_write(create_specifies_module_relationships)
    
driver.close()
