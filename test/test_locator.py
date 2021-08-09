from pytest import approx
from cvts._base_locator import locate_base

def test_locate_base():
    res = locate_base(
        [.2,.2,.2,.2,.2,.2,.2,.2,.2,.2],
        [.2,.2,.2,.2,.2,.2,.2,.2,.2,.2],
        [0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],
        0., 1.,
        0., 1.,
        .1,
        1.)

    assert res[0] == approx(0.2)
    assert res[1] == approx(0.2)
