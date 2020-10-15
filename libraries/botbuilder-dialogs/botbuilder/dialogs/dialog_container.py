# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from abc import ABC, abstractmethod


from .dialog import Dialog
from .dialog_context import DialogContext
from .dialog_event import DialogEvent
from .dialog_events import DialogEvents
from .dialog_set import DialogSet


class DialogContainer(ABC, Dialog):
    def __init__(self, dialog_id: str = None):
        super().__init__(dialog_id)

        self.dialogs = DialogSet()

    @abstractmethod
    def create_child_context(self, dialog_context: DialogContext) -> DialogContext:
        raise NotImplementedError()

    def find_dialog(self, dialog_id: str) -> Dialog:
        # TODO: deprecate DialogSet.find
        return self.dialogs.find_dialog(dialog_id)

    async def on_dialog_event(
        self, dialog_context: DialogContext, dialog_event: DialogEvent
    ) -> bool:
        """
        Called when an event has been raised, using `DialogContext.emitEvent()`, by either the current dialog or a dialog that the current dialog started.
        <param name="dialog_context">The dialog context for the current turn of conversation.</param>
        <param name="e">The event being raised.</param>
        <param name="cancellationToken">The cancellation token.</param>
        <returns>True if the event is handled by the current dialog and bubbling should stop.</returns>
        """
        handled = await super().on_dialog_event(dialog_context, dialog_event)

        # Trace unhandled "versionChanged" events.
        if not handled and dialog_event.name == DialogEvents.version_changed:

            trace_message = f"Unhandled dialog event: {dialog_event.name}. Active Dialog: {dialog_context.active_dialog.id}"

            # dialog_context.dialogs.telemetry_client.TrackTrace(trace_message, Severity.Warning, null)

            await dialog_context.context.send_trace_activity(trace_message)

        return handled

    def get_internal_version(self) -> str:
        """
        GetInternalVersion - Returns internal version identifier for this container.
        DialogContainers detect changes of all sub-components in the container and map that to an DialogChanged event.
        Because they do this, DialogContainers "hide" the internal changes and just have the .id. This isolates changes
        to the container level unless a container doesn't handle it.  To support this DialogContainers define a
        protected virtual method GetInternalVersion() which computes if this dialog or child dialogs have changed
        which is then examined via calls to check_for_version_change_async().
        <returns>version which represents the change of the internals of this container.</returns>
        """
        return self.dialogs.get_internal_version()

    async def check_for_version_change_async(self, dialog_context: DialogContext):
        """
        <param name="dialog_context">dialog context.</param>
        <param name="cancellationToken">cancellationToken.</param>
        <returns>task.</returns>
        Checks to see if a containers child dialogs have changed since the current dialog instance
        was started.
        
        This should be called at the start of `beginDialog()`, `continueDialog()`, and `resumeDialog()`.
        """
        current = dialog_context.active_dialog.version
        dialog_context.active_dialog.version = self.get_internal_version()

        # Check for change of previously stored hash
        if current and current != dialog_context.active_dialog.version:
            # Give bot an opportunity to handle the change.
            # - If bot handles it the changeHash will have been updated as to avoid triggering the
            #   change again.
            await dialog_context.emit_event(
                DialogEvents.version_changed, self.id, True, False
            )
