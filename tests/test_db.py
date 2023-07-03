from corna.db.models import TestTable

def test_corna_simple_db_test(session):

    session.add(TestTable(id=1, description="test1"))
    session.commit()
    result = (
        session.query(TestTable)
        .filter(TestTable.description == "test1")
        .one()
    )

    assert result.id == 1
    assert result.description == "test1"
