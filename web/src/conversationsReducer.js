/**
 * Reducer for conversations.
 * @param {Array} conversations 
 * @param {string} conversation.id
 * @param {string} conversation.title
 * @param {Array} conversation.messages
 * @param {boolean} conversation.active
 * @param {*} action 
 * @returns 
 */
export const conversationsReducer = (conversations, action) => {
    switch (action.type) {
        case "added": {
            // new conversation will be added to the first and be activated.
            return [
                { ...action.conversation, messages: [], active: true },
                ...conversations.map(c => { return { ...c, active: false } }),
            ];
        }
        case "deleted": {
            return conversations.filter((c) => c.id !== action.id);
        }
        case "updated": {
            return conversations.map((c) => {
                if (c.id !== action.conversation.id) {
                    return c;
                }
                return { ...c, ...action.conversation };
            });
        }
        case "selected": {
            return conversations.map((c) => {
                if (c.id === action.data.id) {
                    return {
                        ...action.data,
                        active: true,
                    };
                } else {
                    return {
                        ...c,
                        active: false,
                    };
                }
            });
        }
        case "moveToFirst": {
            const toMove = conversations.find((c) => {
                return c.id === action.id;
            })
            const others = conversations.filter((c) => c.id !== action.id);
            return [toMove, ...others];
        }
        case "replaceAll": {
            // set the first conversation to be active
            return [{ ...action.conversations[0], active: true }, ...action.conversations.slice(1).map((c) => { return { ...c, active: false } })]
        }
        case "messageAdded": {
            return conversations.map((c) => {
                if (c.id !== action.id) {
                    return c;
                }
                return { ...c, messages: [...c.messages, action.message] };
            });
        }
        case "messageAppended": {
            return conversations.map((c) => {
                if (c.id !== action.id) {
                    return c;
                }
                const lastMsg = c.messages[c.messages.length - 1];
                return {
                    ...c,
                    messages: [...c.messages.slice(0, -1), { ...lastMsg, content: lastMsg.content + action.message.content }]
                };
            });
        }
        case "stepsAdded": {
            return conversations.map((c) => {
                if (c.id !== action.id) {
                    return c;
                }
                return {
                    ...c,
                    messages: c.messages.map((msg) => msg.id === action.message.id ? { ...msg, intermediate_steps: action.message.content } : msg)
                };
            });
        }
        default: {
            throw Error("Unknown action: " + action.type);
        }
    }
};

export const getCurrentConversation = (conversations) => {
    return conversations.find((c) => c.active);
}

export const getConversationById = (conversations, id) => {
    return conversations.find((c) => c.id === id);
}
