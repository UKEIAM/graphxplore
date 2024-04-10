import pytest
from typing import Tuple
from graphxplore.Basis import GraphDatabaseUtils

def port_checker(value):
    try:
        int(value)
    except ValueError:
        raise pytest.UsageError('Commandline option "--neo4j_port" must be an integer')
    return value

def pytest_addoption(parser):
    parser.addoption("--run_neo4j_tests", action="store", default="False", choices=("True", "False"),
                     help="Flag to test read/write to Neo4J database. Defaults to 'False'")
    parser.addoption("--neo4j_host", action="store", default="localhost",
                     help="Host of Neo4J DBMS. Defaults to 'localhost'")
    parser.addoption("--neo4j_port", action="store", default="7687", type=port_checker,
                     help="Bolt port of Neo4J DBMS. Defaults to '7687'")
    parser.addoption("--neo4j_user", action="store", default="neo4j",
                     help="Username to access Neo4J DBMS. Defaults to 'neo4j'")
    parser.addoption("--neo4j_pwd", action="store", default="",
                     help="Password to access Neo4J DBMS. Defaults to ''(empty string)")

@pytest.fixture
def neo4j_config(request)->Tuple[bool, str, Tuple[str, str]]:
    run_test = True if request.config.getoption("--run_neo4j_tests") == 'True' else False
    address = GraphDatabaseUtils.get_neo4j_address(request.config.getoption("--neo4j_host"),
                                                   int(request.config.getoption("--neo4j_port")))
    auth = (request.config.getoption("--neo4j_user"), request.config.getoption("--neo4j_pwd"))
    return run_test, address, auth