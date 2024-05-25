//==============================================================================
/*!
//  \file
//  \brief Defines python bindings for a \elastica vector view
//
//  Copyright (C) 2020-2022 Tejaswin Parthasarathy - All Rights Reserved
//  Copyright (C) 2020-2022 MattiaLab - All Rights Reserved
//
//  Distributed under the MIT License.
//  See LICENSE.txt for details.
*/
//==============================================================================

//******************************************************************************
// Includes
//******************************************************************************

//
#include "Utilities/DefineTypes.h"  // real_t
#include "Utilities/Math/Python/SubVectorHelpers.hpp"
//
#include <pybind11/pybind11.h>
//
#include <blaze/math/DynamicVector.h>
#include <blaze/math/Subvector.h>

namespace py = pybind11;

namespace py_bindings {

  //****************************************************************************
  /*!\brief Helps bind a vector view in \elastica
   * \ingroup python_bindings
   */
  void bind_blaze_subvector(py::module& m) {  // NOLINT

    using Real = ::elastica::real_t;
    using data_type = ::blaze::DynamicVector<Real, ::blaze::columnVector,
                                             ::blaze::AlignedAllocator<Real>>;
    using type = ::blaze::Subvector_<data_type, ::blaze::unaligned>;

    // Wrapper for basic DataVector operations
    auto py_vector_view =
        py::class_<type>(m, "VectorView", py::buffer_protocol());
    bind_blaze_subvector_helper(py_vector_view);
  }
  //****************************************************************************

}  // namespace py_bindings
