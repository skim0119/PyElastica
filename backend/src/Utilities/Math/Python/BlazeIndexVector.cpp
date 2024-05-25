//==============================================================================
/*!
//  \file
//  \brief Defines python bindings for a \elastica index vector type
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
#include "Utilities/PrettyType.hpp"
#include "Utilities/PrintHelpers.hpp"
//
#include "Utilities/Math/Python/SliceHelpers.hpp"
//
#include <algorithm>
#include <cstdint>  // size_t
#include <memory>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>
//
#include <pybind11/operators.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
//
#include <blaze/math/DynamicVector.h>
//

namespace py = pybind11;

namespace py_bindings {

  //****************************************************************************
  /*!\brief Helps bind a index_vector type in \elastica
   * \ingroup python_bindings
   */
  void bind_blaze_index_vector(py::module& m) {  // NOLINT

    using Index = std::size_t;
    using type = ::blaze::DynamicVector<Index, ::blaze::columnVector,
                                        ::blaze::AlignedAllocator<Index>>;
    // Wrapper for basic DataVector operations
    auto py_vector =
        py::class_<type>(m, "IndexVector", py::buffer_protocol())
            .def(py::init<std::size_t>(), py::arg("size"))
            .def(py::init<std::size_t, Index>(), py::arg("size"),
                 py::arg("fill"))
            .def(py::init([](std::vector<Index> const& values) {
                   type result(values.size());
                   std::copy(values.begin(), values.end(), result.begin());
                   return result;
                 }),
                 py::arg("values"))
            .def(py::init([](py::buffer buffer) {
                   py::buffer_info info = buffer.request();
                   // Sanity-check the buffer
                   if (info.format != py::format_descriptor<Index>::format()) {
                     throw std::runtime_error(
                         "Incompatible format: expected a " +
                         ::pretty_type::short_name<Index>() +
                         " array, corresponding to " +
                         py::format_descriptor<Index>::format() +
                         ". Got type " + info.format);
                   }
                   if (info.ndim != 1) {
                     throw std::runtime_error("Incompatible dimension.");
                   }
                   const auto size = static_cast<std::size_t>(info.shape[0]);
                   auto data = static_cast<Index*>(info.ptr);
                   type result(size);
                   std::copy_n(data, result.size(), result.begin());
                   return result;
                 }),
                 py::arg("buffer"))
            // Expose the data as a Python buffer so it can be cast into Numpy
            // arrays
            .def_buffer([](type& t) {
              return py::buffer_info(t.data(),
                                     // Size of one scalar
                                     sizeof(Index),
                                     py::format_descriptor<Index>::format(),
                                     // Number of dimensions
                                     1,
                                     // Size of the buffer
                                     {t.size()},
                                     // Stride for each index (in bytes)
                                     {sizeof(Index)});
            })
            .def(
                "__iter__",
                [](const type& t) {
                  return py::make_iterator(t.begin(), t.end());
                },
                // Keep object alive while iterator exists
                py::keep_alive<0, 1>())
            // __len__ is for being able to write len(my_data_vector) in python
            .def("__len__", [](const type& t) { return t.size(); })
            .def_property_readonly(
                "shape",
                +[](const type& t) {
                  return std::tuple<std::size_t>(t.size());
                })
            // __getitem__ and __setitem__ are the subscript operators
            // (operator[]). To define (and overload) operator() use __call__
            .def(
                "__getitem__",
                +[](const type& t, const size_t i) {
                  bounds_check(t, i);
                  return t[i];
                })
            .def(
                "__getitem__",
                +[](type& t, const py::slice slice) {
                  return array_slice(t, std::move(slice));
                })
            .def(
                "__setitem__", +[](type& t, const size_t i, const Index v) {
                  bounds_check(t, i);
                  t[i] = v;
                });

    static const auto printer = [](type const& t) {
      // Blaze's default printing adds extra lines and spaces which is
      // not what we want
      std::ostringstream os;
      sequence_print_helper(os, t.begin(), t.end());
      return os.str();
    };

    // Need __str__ for converting to string/printing
    py_vector
        .def("__str__", +printer)
        // repr allows you to output the object in an interactive python
        // terminal using obj to get the "string REPResenting the object".
        .def("__repr__", +printer)
        .def(py::self == py::self)
        .def(py::self != py::self);
    // Index vectors need not be addable/subtractable, so no operators are
    // provided
  }
  //****************************************************************************

}  // namespace py_bindings
