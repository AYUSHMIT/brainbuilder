'''main circuit building worklfow'''
import os
import numpy as np

from brainbuilder.utils import genbrain as gb
from brainbuilder.orientation_fields import compute_sscx_orientation_fields
from brainbuilder.select_region import select_region
from brainbuilder.cell_positioning import cell_positioning
from brainbuilder.assignment_synapse_class import assign_synapse_class_from_recipe
from brainbuilder.assignment_metype import assign_metype
from brainbuilder.assignment_morphology import assign_morphology
from brainbuilder.assignment_orientation import assign_orientations
from brainbuilder.assignment_orientation import randomise_orientations
from brainbuilder.export_bbp import export_for_bbp

import logging


def main(data_dir):  # pylint: disable=R0914
    '''
    Most of the workflow steps here replace BlueBuilder.

    The logic is organised around voxel data.
    The idea being that voxel data allows me to isolate region-specific logic from the general
    circuit building workflow.

    This leaves out Morphology Repair and Neuron model fitting (OptimizerFramework/ModelManagement).

    The params that have values assigned are actual "workflow parameters"
    that need to be given by a user.

    The variables imply a data dependency: note that many of the steps could be sorted differently.

    The first two steps are SSCx-specific code. From there, the code is generic.
    '''

    annotation_mhd, annotation_raw = gb.load_meta_io(
        os.path.join(data_dir, 'P56_Mouse_annotation/annotation.mhd'),
        os.path.join(data_dir, 'P56_Mouse_annotation/annotation.raw'))

    annotation = gb.MetaIO(annotation_mhd, annotation_raw)

    hierarchy = gb.load_hierarchy(
        os.path.join(data_dir, 'P56_Mouse_annotation/annotation_hierarchy.json'))['msg'][0]

    full_density_mhd, full_density_raw = gb.load_meta_io(
        os.path.join(data_dir, 'atlasVolume/atlasVolume.mhd'),
        os.path.join(data_dir, 'atlasVolume/atlasVolume.raw'))
    full_density = gb.MetaIO(full_density_mhd, full_density_raw)

    recipe_filename = os.path.join(data_dir, 'bbp_recipe/builderRecipeAllPathways.xml')
    neurondb_filename = os.path.join(data_dir, 'prod_NeuronDB_19726.dat')

    #region_name = 'Primary somatosensory area'
    #total_cell_count = 4000000
    #rotation_ranges = ((0, 0), (0, 2 * np.pi), (0, 0))
    #region_acronym = 'SSp-ll'
    region_name = "Primary somatosensory area, lower limb"
    total_cell_count = 400000
    rotation_ranges = ((0, 0), (0, 2 * np.pi), (0, 0))
    #inhibitory_proportion = 0.10

    voxel_dimensions = full_density.mhd['ElementSpacing']

    logging.basicConfig()

    ################################################################################################

    density_raw = select_region(annotation.raw, full_density.raw, hierarchy, region_name)

    orientation_field = compute_sscx_orientation_fields(annotation, hierarchy, region_name)

    positions = cell_positioning(density_raw, voxel_dimensions, total_cell_count)

    orientations = assign_orientations(positions, orientation_field, voxel_dimensions)

    orientations = randomise_orientations(orientations, rotation_ranges)

    chosen_synapse_class = assign_synapse_class_from_recipe(positions, annotation,
                                                            hierarchy, recipe_filename, region_name)

    chosen_me = assign_metype(positions, chosen_synapse_class, annotation,
                              hierarchy, recipe_filename, region_name)

    chosen_morphology = assign_morphology(positions, chosen_me, annotation, hierarchy,
                                          recipe_filename, neurondb_filename)

    ################################################################################################

    circuit = export_for_bbp(positions, orientations,
                             (chosen_synapse_class, chosen_me, chosen_morphology))

    return circuit


if __name__ == "__main__":
    main('../data')
