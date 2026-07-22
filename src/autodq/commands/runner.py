from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from autodq.commands.cells import ADQLCellParser
from autodq.commands.errors import (
    ADQLExecutionError,
    ADQLValidationError,
)
from autodq.commands.executor import ADQLExecutor
from autodq.commands.models import (
    ADQLCellRun,
    ADQLFileResult,
    ADQLRunResult,
    ADQLScript,
)
from autodq.commands.parser import ADQLParser
from autodq.commands.validator import ADQLValidator


class ADQLFileRunner:
    """Inspect, validate, and execute standalone cell-based ADQL files."""

    def __init__(
        self,
        *,
        parser: ADQLParser | None = None,
        validator: ADQLValidator | None = None,
        executor: ADQLExecutor | None = None,
        cell_parser: ADQLCellParser | None = None,
    ):
        self.parser = parser or ADQLParser()
        self.validator = validator or ADQLValidator()
        self.executor = executor or ADQLExecutor()
        self.cell_parser = cell_parser or ADQLCellParser()

    def inspect(self, path: str | Path):
        """Return the parsed document and its notebook-style cells."""
        return self.cell_parser.read(path)

    def validate(
        self,
        path: str | Path,
        *,
        dataset: str | Path | None = None,
    ):
        """Validate a standalone ADQL file without running it."""
        document = self.inspect(path)
        script = self._document_script(document)
        self.validator.validate(script)
        self._standalone_dataset(script, document.path, dataset=dataset)
        return document

    def run(
        self,
        path: str | Path,
        *,
        dataset: str | Path | None = None,
        target: str | None = None,
        cell: int | None = None,
        through_cell: int | None = None,
        continue_on_error: bool = False,
        raise_on_error: bool = False,
        auto_display: bool = False,
    ) -> ADQLFileResult:
        """Run a self-contained ADQL file and return its project and outputs."""
        document = self.inspect(path)
        script = self._document_script(document)
        self.validator.validate(script)
        dataset_path, declared_target = self._standalone_dataset(
            script,
            document.path,
            dataset=dataset,
        )
        effective_target = target if target is not None else declared_target

        # Imported here so the command package never creates a circular import
        # with the main project controller.
        from autodq.core.project import AutoDQ

        project = AutoDQ(str(dataset_path), target=effective_target)
        return self.run_with_project(
            project,
            document.path,
            cell=cell,
            through_cell=through_cell,
            continue_on_error=continue_on_error,
            raise_on_error=raise_on_error,
            auto_display=auto_display,
            dataset_override=(dataset_path if dataset is not None else None),
            target_override=target,
            document=document,
        )

    def run_with_project(
        self,
        project,
        path: str | Path,
        *,
        cell: int | None = None,
        through_cell: int | None = None,
        continue_on_error: bool = False,
        raise_on_error: bool = True,
        auto_display: bool = False,
        dataset_override: str | Path | None = None,
        target_override: str | None = None,
        document=None,
    ) -> ADQLFileResult:
        """Run an ADQL document against an existing AutoDQ project."""
        if cell is not None and through_cell is not None:
            raise ValueError("Use either cell or through_cell, not both.")

        document = document or self.inspect(path)
        full_script = self._document_script(document)
        self.validator.validate(full_script)
        selected_cells = self._select_cells(
            document,
            cell=cell,
            through_cell=through_cell,
        )
        file_result = ADQLFileResult(
            document=document,
            project=project,
            auto_display=auto_display,
        )

        for document_cell in selected_cells:
            if document_cell.kind == "markdown" or not self.cell_parser._has_executable_source(
                document_cell.source
            ):
                empty_run = ADQLRunResult(
                    script=ADQLScript(
                        source=document_cell.source,
                        statements=[],
                    ),
                    source_name=self._cell_source_name(
                        document.path,
                        document_cell.number,
                    ),
                    finished_at=datetime.now(),
                    auto_display=False,
                )
                file_result.cell_runs.append(
                    ADQLCellRun(cell=document_cell, result=empty_run)
                )
                continue

            script = self.parser.parse(document_cell.source)
            self.validator.validate(script)
            script = self._apply_overrides(
                script,
                dataset_override=dataset_override,
                target_override=target_override,
            )

            try:
                run_result = self.executor.execute(
                    project,
                    script,
                    continue_on_error=continue_on_error,
                    auto_display=False,
                    source_name=self._cell_source_name(
                        document.path,
                        document_cell.number,
                    ),
                    base_path=document.path.parent,
                )
            except ADQLExecutionError as error:
                run_result = error.result

                if run_result is not None:
                    project._record_adql_run(run_result)
                    file_result.cell_runs.append(
                        ADQLCellRun(cell=document_cell, result=run_result)
                    )

                file_result.finished_at = datetime.now()

                if raise_on_error:
                    error.file_result = file_result
                    raise

                break

            project._record_adql_run(run_result)
            file_result.cell_runs.append(
                ADQLCellRun(cell=document_cell, result=run_result)
            )

        file_result.finished_at = datetime.now()
        return file_result

    @staticmethod
    def _standalone_dataset(script, path: Path, *, dataset=None):
        declarations = [
            statement
            for statement in script.statements
            if statement.kind == "DATASET"
        ]

        if len(declarations) > 1:
            raise ADQLValidationError(
                "A standalone ADQL file can declare DATASET only once."
            )

        if declarations and script.statements[0].kind != "DATASET":
            raise ADQLValidationError(
                "DATASET must be the first statement in a standalone ADQL file."
            )

        if dataset is None and not declarations:
            raise ADQLValidationError(
                "A standalone ADQL file must begin with DATASET, or be run "
                "with --dataset."
            )

        declared_target = (
            declarations[0].parameters.get("target")
            if declarations
            else None
        )
        candidate = (
            Path(dataset).expanduser()
            if dataset is not None
            else Path(declarations[0].parameters["dataset_path"]).expanduser()
        )

        if not candidate.is_absolute():
            candidate = (
                (Path.cwd() if dataset is not None else path.parent)
                / candidate
            )

        return candidate.resolve(), declared_target

    @staticmethod
    def _select_cells(document, *, cell=None, through_cell=None):
        if cell is not None:
            if cell < 1:
                raise ValueError("cell must be 1 or greater.")

            return [document.cell(cell)]

        if through_cell is not None:
            if through_cell < 1:
                raise ValueError("through_cell must be 1 or greater.")

            document.cell(through_cell)
            return [
                item
                for item in document.cells
                if item.number <= through_cell
            ]

        return list(document.cells)

    @staticmethod
    def _apply_overrides(
        script,
        *,
        dataset_override=None,
        target_override=None,
    ):
        if dataset_override is None and target_override is None:
            return script

        statements = []

        for statement in script.statements:
            if statement.kind != "DATASET":
                statements.append(statement)
                continue

            parameters = dict(statement.parameters)

            if dataset_override is not None:
                parameters["dataset_path"] = str(dataset_override)

            if target_override is not None:
                parameters["target"] = target_override

            statements.append(replace(statement, parameters=parameters))

        return replace(script, statements=statements)

    @staticmethod
    def _cell_source_name(path: Path, number: int) -> str:
        return f"{path.resolve()}#cell={number}"

    def _document_script(self, document):
        source = "\n".join(
            cell.source
            for cell in document.cells
            if cell.kind == "code"
            and self.cell_parser._has_executable_source(cell.source)
        )

        if not source.strip():
            raise ADQLValidationError(
                "An ADQL document must contain at least one executable code cell."
            )

        return self.parser.parse(source)
