//==============================================================================
/*!
//  \file
//  \brief Defines python bindings for a \elastica tensor view
//
//  Copyright (C) 2020-2022 Tejaswin Parthasarathy - All Rights Reserved
//  Copyright (C) 2020-2022 MattiaLab - All Rights Reserved
//
//  Distributed under the MIT License.
//  See LICENSE.txt for details.
*/
//==============================================================================

//
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
#include <blaze_tensor/math/DynamicTensor.h>
#include <blaze_tensor/math/Subtensor.h>

namespace py = pybind11;

namespace py_bindings {

  //****************************************************************************
  /*!\brief Helps bind a tensor view in \elastica
   * \ingroup python_bindings
   */
  void bind_blaze_subtensor(py::module& m) {  // NOLINT
    using Real = ::elastica::real_t;
    using data_type = ::blaze::DynamicTensor<Real>;
    using type = ::blaze::Subtensor<data_type, ::blaze::unaligned>;

    // Wrapper for basic type operations
    py::class_<type>(m, "TensorView", py::buffer_protocol())
        // Expose the data as a Python buffer so it can be cast into Numpy
        // arrays
        .def_buffer([](type& tensor) {
          return py::buffer_info(
              tensor.data(),
              // Size of one scalar
              sizeof(Real), py::format_descriptor<Real>::format(),
              // Number of dimensions
              3,
              // Size of the buffer
              {tensor.pages(), tensor.rows(), tensor.columns()},
              // Stride for each index (in bytes). Data is stored
              // in column-major layout (see `type.hpp`).
              {sizeof(Real) * tensor.rows() * tensor.spacing(),
               sizeof(Real) * tensor.spacing(), sizeof(Real)});
        })
        .def_property_readonly(
            "shape",
            +[](const type& self) {
              return std::tuple<std::size_t, std::size_t, std::size_t>(
                  self.pages(), self.rows(), self.columns());
            })
        // __getitem__ and __setitem__ are the subscript operators (M[*,*]).
        .def(
            "__getitem__",
            +[](const type& self,
                const std::tuple<std::size_t, std::size_t, std::size_t>& x) {
              tensor_bounds_check(self, std::get<0>(x), std::get<1>(x),
                                  std::get<2>(x));
              return self(std::get<0>(x), std::get<1>(x), std::get<2>(x));
            })
        .def(
            "__getitem__",
            +[](type& self, std::tuple<py::slice, py::slice, py::slice> slice) {
              return array_slice(self, std::move(slice));
            })
        .def(
            "__setitem__",
            +[](type& self,
                const std::tuple<std::size_t, std::size_t, std::size_t>& x,
                const Real val) {
              tensor_bounds_check(self, std::get<0>(x), std::get<1>(x),
                                  std::get<2>(x));
              self(std::get<0>(x), std::get<1>(x), std::get<2>(x)) = val;
            })
        .def(
            "__str__", +[](const type& self) {
              return std::string(MakeString{} << self);
            });
  }
  //****************************************************************************

}  // namespace py_bindings
