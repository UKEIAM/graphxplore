from graphxplore.Basis import GraphDatabaseUtils

RUN_DB_TESTS = False
NEO4J_HOST = 'localhost'
NEO4J_PROTOCOL = 'bolt'
NEO4J_PORT = 7687
NEO4J_AUTH = ('neo4j', '')

def get_neo4j_address() -> str:
    return GraphDatabaseUtils.get_neo4j_address(NEO4J_HOST, NEO4J_PORT, NEO4J_PROTOCOL)

def test_connectivity() -> bool:
    try:
        GraphDatabaseUtils.test_connection(get_neo4j_address(), NEO4J_AUTH)
        return True
    except ValueError:
        return False