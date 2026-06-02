"""
RBAC matrix tests.

Each row in the matrix asserts what HTTP status each role gets for a given endpoint.
Populated in P2 as endpoints are built.

Format (to be filled in):
    @pytest.mark.parametrize("role,expected_status", [
        ("patient",     200),
        ("doctor",      403),
        ("coordinator", 403),
        ("super_admin", 200),
    ])
    async def test_get_own_profile(role, expected_status, ...):
        ...
"""
