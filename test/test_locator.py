from pytest import approx
from cvts._base_locator import locate_base
from cvts import rawfiles2jsonchunks

def test_locate_base():
    res = locate_base(
        [.2,.2,.2,.2,.2,.2,.2,.2,.2,.2],
        [.2,.2,.2,.2,.2,.2,.2,.2,.2,.2],
        [0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],
        0., 1.,
        0., 1.,
        (.1, .05, .003),
        1.)
    assert res[0] == approx(0.2)
    assert res[1] == approx(0.2)

def test_locate_base_2():
    res, _ = rawfiles2jsonchunks('test.csv', True)
    print(res)
    assert res[0] == approx(108.18927950)
    assert res[1] == approx( 11.08898850)
