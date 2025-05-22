# arcane2graph

## Executer arcane en sequentiel avec les options suivantes
```
-A,export_format=xml,export_output_directory=[path],export_only=true
```
!!! export_only sert à tuer le processus avant le lancement de la simultation en provoquant une erreur, l'erreur est donc normale.


## Convertir les configs .xml extraitent via arcane en .json
```
python converToJson.py
```

## convertir les .axl en .json via axlstar
```
axl2ccT4 -l json -o \[output_path\] \[path_to_axl\]/Mahyco.axl
```

## Déploiement docker
```
docker run \
    -d \
    -p 7474:7474 -p 7687:7687 \
    -v $PWD/data:/data -v $PWD/plugins:/plugins \
    --name neo4j-apoc \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    -e NEO4J_PLUGINS=\[\"apoc\",\"apoc-extended\"\] \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:5.26
```

## Remplir la BDD

Lancer ```merge.py``` en premier puis ```export_axl.py```

## Interface web
```
http://localhost:7474/browser/
```

## couple specification instance pour l'option nommée ...
```
MATCH p=(o: Option {fullName: "Mahyco/boundary-condition"})-[r:SPECIFIES]->()
return p
```

## Couverture de toutes les options
```
MATCH (o)-[:SPECIFIES]->(n)
WITH apoc.map.clean(properties(n), ['uid'], []) AS props, coalesce(o.fullName, o.name) AS name
UNWIND keys(props) AS key
RETURN name, key, props[key] AS value, count(*) AS count
ORDER BY name, count DESC;
```
