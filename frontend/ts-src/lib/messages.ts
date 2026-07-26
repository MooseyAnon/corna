/* Message protocol shared between the host and toolbar.
 
The toolbar (TB) is the core navigation control panel offered to users. The TB
is injected into each page using an iframe. We use message passing as a way
to communicate between the iframe context and the parent page context it sits
inside.

This message lib ensures the two contexts pass messages and communicated in a
verifiable and predicable way.

Terminology definitions:
- host = the main page which hosts the TB iframe
- toolbar = the iframe control panel injected into a page on the client

We use these terms as message namespaces so both sides can correctly validate
incoming message.
*/

export const MESSAGE_VERSION = 1 as const;


/**
 * Messages sent from the toolbar to the host.
 */
export type ToolbarMessageType =
    | "toolbar:open"
    | "toolbar:close"
    | "toolbar:navigate"
    | "toolbar:ready";


/**
 * Messages sent from the host to the toolbar.
 *
 * No host messages are currently implemented, but the type is defined now so
 * both sides of the protocol have a clear boundary.
 */
export type HostMessageType =
    | "host:intent";


export type MessageType =
    | ToolbarMessageType
    | HostMessageType;


/**
 * Base message envelope.
 */
export interface Message<T extends MessageType, P> {
    version: typeof MESSAGE_VERSION;
    type: T;
    payload: P;
}


/**
 * Toolbar message payloads.
 */
export type ToolbarOpenMessage = Message<
    "toolbar:open",
    Record<string, never>
>;

export type ToolbarCloseMessage = Message<
    "toolbar:close",
    Record<string, never>
>;

export type ToolbarNavigateMessage = Message<
    "toolbar:navigate",
    {
        domainName: string;
    }
>;

export type ToolbarReadyMessage = Message<
    "toolbar:ready",
    Record<string, never>
>;

export type ToolbarMessage =
    | ToolbarOpenMessage
    | ToolbarCloseMessage
    | ToolbarNavigateMessage
    | ToolbarReadyMessage;


/**
 * Host message payloads.
 */
export type HostIntentMessage<
    P extends object = Record<string, unknown>
> = Message<
    "host:intent",
    {
        intent: string;
        data?: P;
    }
>;


export type HostMessage =
    | HostIntentMessage<Record<string, unknown>>;


/**
 * Create a protocol message.
 *
 * Runtime validation will be added separately. For now this ensures all
 * messages created by our code use the same envelope.
 */
export function createMessage<T extends MessageType, P>(
    type: T,
    payload: P,
): Message<T, P> {
    return {
        version: MESSAGE_VERSION,
        type,
        payload,
    };
}
