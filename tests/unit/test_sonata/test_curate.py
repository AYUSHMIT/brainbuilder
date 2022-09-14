import morphio
import shutil
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from pathlib import Path
import h5py
import numpy as np

import pytest

from brainbuilder.utils import bbp
from brainbuilder.utils.sonata import curate


TEST_DATA_PATH = Path(__file__).parent.parent / 'data'
DATA_PATH = TEST_DATA_PATH / 'sonata' / 'curate'
NODES_FILE = DATA_PATH / 'nodes.h5'
EDGES_FILE = DATA_PATH / 'edges.h5'


@contextmanager
def _copy_file(file):
    with TemporaryDirectory() as tmpdir:
        shutil.copy2(str(file), tmpdir)
        yield Path(tmpdir) / file.name


def test_get_popualtion_names():
    assert ['not-default'] == curate.get_population_names(NODES_FILE)
    assert ['not-default'] == curate.get_population_names(EDGES_FILE)

    with _copy_file(NODES_FILE) as edges_copy_file:
        with h5py.File(edges_copy_file, 'r+') as h5f:
            del h5f['/nodes']
        with pytest.raises(AssertionError):
            curate.get_population_names(edges_copy_file)

    with _copy_file(EDGES_FILE) as edges_copy_file:
        with h5py.File(edges_copy_file, 'r+') as h5f:
            del h5f['/edges']
        with pytest.raises(AssertionError):
            curate.get_population_names(edges_copy_file)


def test_get_population_name():
    assert 'not-default' == curate.get_population_name(NODES_FILE)
    assert 'not-default' == curate.get_population_name(EDGES_FILE)

    with pytest.raises(ValueError):
        curate.get_population_name(EDGES_FILE, 'unknown')

    with _copy_file(NODES_FILE) as nodes_copy_file:
        with h5py.File(nodes_copy_file, 'r+') as h5f:
            h5f['nodes'].create_group('2nd_population')
        with pytest.raises(AssertionError):
            curate.get_population_name(nodes_copy_file)


def test_rename_node_population():
    with _copy_file(NODES_FILE) as nodes_copy_file:
        curate.rename_node_population(nodes_copy_file, 'newname')
        assert ['newname'] == curate.get_population_names(nodes_copy_file)
    with _copy_file(NODES_FILE) as nodes_copy_file:
        curate.rename_node_population(nodes_copy_file, 'newname', 'not-default')
        assert ['newname'] == curate.get_population_names(nodes_copy_file)


def test_rename_edge_population():
    with _copy_file(EDGES_FILE) as edges_copy_file:
        curate.rename_edge_population(edges_copy_file, 'newname')
        assert ['newname'] == curate.get_population_names(edges_copy_file)
    with _copy_file(EDGES_FILE) as edges_copy_file:
        curate.rename_edge_population(edges_copy_file, 'newname', 'not-default')
        assert ['newname'] == curate.get_population_names(edges_copy_file)


def test_add_edge_type_id():
    with _copy_file(EDGES_FILE) as edges_copy_file:
        with h5py.File(edges_copy_file, 'r+') as h5f:
            del h5f['edges/not-default/edge_type_id']
        curate.add_edge_type_id(edges_copy_file, 'not-default')
        with h5py.File(edges_copy_file, 'r') as h5f:
            edge_type_id = np.asarray(h5f['edges/not-default/edge_type_id'])
            assert (edge_type_id == -1).all()


def test_set_nodes_attribute():
    with _copy_file(NODES_FILE) as nodes_copy_file:
        with h5py.File(nodes_copy_file, 'r+') as h5f:
            del h5f['nodes/not-default/0/model_type']
        curate.set_group_attribute(
            nodes_copy_file, 'nodes', 'not-default', '0', 'model_type', 'biophysical')
        with h5py.File(nodes_copy_file, 'r') as h5f:
            assert [b'biophysical'] == h5f['nodes/not-default/0/@library/model_type'][:].tolist()
            model_type = np.asarray(h5f['nodes/not-default/0/model_type'])
            assert model_type.dtype == int
            assert (model_type == 0).all()


def test_set_edges_attribute():
    with _copy_file(EDGES_FILE) as edges_copy_file:
        curate.set_group_attribute(
            edges_copy_file, 'edges', 'not-default', '0', 'syn_weight', 2.2, True)
        with h5py.File(edges_copy_file, 'r') as h5f:
            syn_weight = np.asarray(h5f['edges/not-default/0/syn_weight'])
            assert syn_weight.dtype == float
            assert (syn_weight == 2.2).all()


def test_rewire_edge_population():
    with _copy_file(EDGES_FILE) as edges_copy_file, _copy_file(NODES_FILE) as nodes_copy_file:
        curate.rename_node_population(nodes_copy_file, 'newname')
        curate.rewire_edge_population(edges_copy_file, nodes_copy_file, nodes_copy_file, 'chemical')
        expected_name = 'newname__newname__chemical'
        assert [expected_name] == curate.get_population_names(edges_copy_file)
        with h5py.File(edges_copy_file, 'r') as h5f:
            expected_name = '/edges/' + expected_name
            assert 'newname' == h5f[expected_name]['source_node_id'].attrs['node_population']
            assert 'newname' == h5f[expected_name]['target_node_id'].attrs['node_population']


def test_create_projection_source_nodes():
    projection_file = DATA_PATH / 'projection.h5'
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_nodes_file = curate.create_projection_source_nodes(
            projection_file, tmpdir, 'projections', fix_offset=False)
        assert source_nodes_file.stem == 'nodes_projections'
        assert ['projections', ] == curate.get_population_names(source_nodes_file)
        with h5py.File(source_nodes_file, 'r') as h5f:
            assert [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ] == h5f['/nodes/projections/0/model_type'][:].tolist()

        source_nodes_file = curate.create_projection_source_nodes(
            projection_file, tmpdir, 'projections', fix_offset=True)
        assert source_nodes_file.stem == 'nodes_projections'
        assert ['projections', ] == curate.get_population_names(source_nodes_file)
        with h5py.File(source_nodes_file, 'r') as h5f:
            assert [b'virtual', b'virtual'] == h5f['/nodes/projections/0/model_type'][:].tolist()

def test_correct_source_nodes_offset():
    with TemporaryDirectory() as tmpdir:
        shutil.copy2(DATA_PATH / 'projection.h5', tmpdir)
        edges_file = Path(tmpdir) / 'projection.h5'
        curate.correct_source_nodes_offset(edges_file,
                                           edge_population_name='not-default',
                                           offset=10)
        with h5py.File(edges_file, 'r') as h5f:
            assert h5f['/edges/not-default/0/syn_weight'].shape == (4, )
            assert [0, 0, 1, 1, ] == h5f['/edges/not-default/source_node_id'][:].tolist()

def test_merge_h5_files():
    with _copy_file(NODES_FILE) as nodes_copy_file:
        curate.rename_node_population(nodes_copy_file, 'newname')
        with TemporaryDirectory() as tmpdir:
            merged_file = Path(tmpdir) / 'merged_nodes.h5'
            curate.merge_h5_files([NODES_FILE, nodes_copy_file], 'nodes', merged_file)
            assert ['newname', 'not-default'] == curate.get_population_names(merged_file)
            with h5py.File(merged_file, 'r') as h5f:
                assert '/nodes/not-default/0' in h5f
                assert '/nodes/newname/0' in h5f

def test__has_unifurcations():
    morph = morphio.Morphology(DATA_PATH / 'wrong-order-with-unifurcations.h5')
    assert curate._has_unifurcations(morph)


def test__has_sonata_ordering():
    morph = morphio.Morphology(DATA_PATH / 'wrong-order-with-unifurcations.h5')
    assert not curate._has_sonata_ordering(morph)


def test_check_morphology_invariants():
    morph_names = bbp.load_extneurondb(str(DATA_PATH / 'neurondbExt.dat')).morphology.to_list()
    incorrect_ordering, have_unifurcations =  curate.check_morphology_invariants(DATA_PATH, morph_names)
    assert incorrect_ordering == {'wrong-order-with-unifurcations'}
    assert have_unifurcations == {'wrong-order-with-unifurcations'}
