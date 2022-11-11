"""`Dataset` class(es) for reading from Parquet files."""

from typing import Any, List, Optional, Tuple, Union, cast

import numpy as np
import awkward as ak

from graphnet.data.dataset import Dataset, ColumnMissingException


class ParquetDataset(Dataset):
    """Pytorch dataset for reading from Parquet files."""

    # Implementing abstract method(s)
    def _init(self) -> None:
        # Check(s)
        if isinstance(self._path, list):
            self.error("Multiple files not supported")
        assert isinstance(self._path, str)

        assert self._path.endswith(
            ".parquet"
        ), f"Format of input file `{self._path}` is not supported"

        assert (
            self._node_truth is None
        ), "Argument `node_truth` is currently not supported."
        assert (
            self._node_truth_table is None
        ), "Argument `node_truth_table` is currently not supported."
        assert (
            self._string_selection is None
        ), "Argument `string_selection` is currently not supported"

        # Set custom member variable(s)
        self._parquet_hook = ak.from_parquet(self._path, lazy=False)

    def _get_all_indices(self) -> np.ndarray:
        return np.arange(
            len(
                ak.to_numpy(
                    self._parquet_hook[self._truth_table][self._index_column]
                ).tolist()
            )
        )

    def _query_table(
        self,
        table: str,
        columns: Union[List[str], str],
        sequential_index: Optional[int] = None,
        selection: Optional[str] = None,
    ) -> List[Tuple[Any, ...]]:
        # Check(s)
        assert (
            selection is None
        ), "Argument `selection` is currently not supported"

        index: Optional[int]
        if sequential_index is None:
            index = None
        else:
            index = cast(List[int], self._indices)[sequential_index]

        try:
            if index is None:
                ak_array = self._parquet_hook[table][columns][index]
            else:
                ak_array = self._parquet_hook[table][columns][:]
        except ValueError as e:
            if "does not exist (not in record)" in str(e):
                raise ColumnMissingException(str(e))
            else:
                raise e

        dictionary = ak_array.to_list()
        assert list(dictionary.keys()) == columns

        if all(map(np.isscalar, dictionary.values())):
            result = [tuple(dictionary.values())]

        else:
            # All arrays should have same length
            array_lengths = [
                len(values)
                for values in dictionary.values()
                if not np.isscalar(values)
            ]
            assert (
                len(set(array_lengths)) == 1
            ), f"Arrays in {dictionary} have differing lengths"
            nb_elements = array_lengths[0]

            # Broadcast scalars
            for key in dictionary:
                value = dictionary[key]
                if np.isscalar(value):
                    dictionary[key] = np.repeat(
                        value, repeats=nb_elements
                    ).tolist()

            result = list(map(tuple, list(zip(*dictionary.values()))))

        return result
