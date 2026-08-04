from dotenv import load_dotenv
load_dotenv()

from adapters.bolt_cypher import BoltCypherAdapter

adapter = BoltCypherAdapter("cognodb")
adapter.connect()

with adapter._driver.session() as session:
    result = session.run("""
        PROFILE
        MATCH (a:Person {id: 1}), (b:Person {id: 2})
        CREATE (a)-[:KNOWS]->(b)
    """)
    summary = result.consume()
    plan = summary.profile
    print(plan)

adapter.close()




