//==============================================================================
/*!
//  \file
//  \brief Defines python bindings for a \elastica matrix view
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
#include "PythonBindings/BoundChecks.hpp"
//
#include "Utilities/DefineTypes.h"
#include "Utilities/MakeString.hpp"
//
#include "Utilities/Math/Python/SliceHelpers.hpp"
//
#include <array>
#include <cstddef>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>
//
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
//
#include <blaze/math/DynamicMatrix.h>
#include <blaze/math/Submatrix.h>
//

namespace py = pybind11;

namespace py_bindings {

  //****************************************************************************
  /*!\brief Helps bind a matrix view in \elastica
   * \ingroup python_bindings
   */
  void bind_blaze_submatrix(py::module& m) {  // NOLINT
    using Real = ::elastica::real_t;
    using data_type = ::blaze::DynamicMatrix<Real, ::blaze::rowMajor,
                                             ::blaze::AlignedAllocator<Real>>;
    using type = ::blaze::Submatrix_<data_type, ::blaze::unaligned>;

    // Wrapper for basic type operations
    py::class_<type>(m, "MatrixView", py::buffer_protocol())
        // Expose the data as a Python buffer so it can be cast into Numpy
        // arrays
        .def_buffer([](type& matrix) {
          return py::buffer_info(
              matrix.data(),
              // Size of one scalar
              sizeof(Real), py::format_descriptor<Real>::format(),
              // Number of dimensions
              2,
              // Size of the buffer
              {matrix.rows(), matrix.columns()},
              // Stride for each index (in bytes). Data is stored
              // in row-major layout (see `type.hpp`).
              {sizeof(Real) * matrix.spacing(), sizeof(Real)});
        })
        .def_property_readonly(
            "shape",
            +[](const type& self) {
              return std::tuple<std::size_t, std::size_t>(self.rows(),
                                                          self.columns());
            })
        // __getitem__ and __setitem__ are the subscript operators (M[*,*]).
        .def(
            "__getitem__",
            +[](const type& self,
                const std::tuple<std::size_t, std::size_t>& x) {
              matrix_bounds_check(self, std::get<0>(x), std::get<1>(x));
              return self(std::get<0>(x), std::get<1>(x));
            })
        .def(
            "__getitem__",
            +[](type& t, std::tuple<py::slice, py::slice> const slice) {
              return array_slice(t, std::move(slice));
            })
        // Need __str__ for converting to string/printing
        .def(
            "__str__",
            +[](const type& self) { return std::string(MakeString{} << self); })
        .def(
            "__setitem__",
            +[](type& self, const std::tuple<std::size_t, std::size_t>& x,
                const Real val) {
              matrix_bounds_check(self, std::get<0>(x), std::get<1>(x));
              self(std::get<0>(x), std::get<1>(x)) = val;
            });
  }
  //****************************************************************************

}  // namespace py_bindings
