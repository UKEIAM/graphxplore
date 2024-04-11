import pytest
import pathlib
ROOT_DIR = str(pathlib.Path(__file__).parents[2])
import sys
sys.path.append(ROOT_DIR)
from graphxplore.Basis import BaseUtils

def test_median():
    assert BaseUtils.calculate_median({}) is None
    assert BaseUtils.calculate_median({1 : 1}) == 1
    assert BaseUtils.calculate_median({1 : 2}) == 1
    assert BaseUtils.calculate_median({1 : 1, 2 : 1}) == 1.5
    assert BaseUtils.calculate_median({1 : 2, 4 : 1}) == 1
    assert BaseUtils.calculate_median({1 : 3, 4 : 1}) == 1

def test_mean_std():
    assert BaseUtils.calculate_std({}) is None
    vals = {1 : 2, 4 : 1}
    assert BaseUtils.calculate_mean(vals) == 2.0
    assert round(BaseUtils.calculate_std(vals), 3) == 1.414

def test_quartiles():
    assert BaseUtils.calculate_median_quartiles({}) is None
    assert BaseUtils.calculate_median_quartiles({1 : 1}) == (1, 1, 1)
    assert BaseUtils.calculate_median_quartiles({1 : 2}) == (1, 1, 1)
    assert BaseUtils.calculate_median_quartiles({1 : 1, 2 : 1}) == (1.5, 1, 2)
    assert BaseUtils.calculate_median_quartiles({1 : 2, 4: 1}) == (1, 1, 4)
    assert BaseUtils.calculate_median_quartiles({1 : 3, 4: 1}) == (1, 1, 2.5)
    assert BaseUtils.calculate_median_quartiles({1: 4, 3000: 1}) == (1, 1, 1)

def test_quintiles():
    assert BaseUtils.calculate_quartile_quintile_sorted_dist([], False, 1) is None
    assert BaseUtils.calculate_quartile_quintile_sorted_dist([(1,3)], False, 1) == 1
    assert BaseUtils.calculate_quartile_quintile_sorted_dist([(1, 1), (2, 4)], False, 1) == 1.5
    assert BaseUtils.calculate_quartile_quintile_sorted_dist([(1, 1), (2, 4)], False, 2) == 2
    assert BaseUtils.calculate_quartile_quintile_sorted_dist([(1, 5), (8999, 1)], False, 4) == 1
    assert BaseUtils.calculate_quartile_quintile_sorted_dist([(1, 4), (8999, 1)], False, 4) == 4500

if __name__ == '__main__':
    pytest.main()