import "./App.css";
import { useState, useEffect, useReducer, useRef, forwardRef } from "react";

import MuiAlert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";

import SideMenu from "components/SideMenu";
import ChatLog from "components/ChatLog";
import ChatMessage from "components/ChatLog/ChatMessage";
import ChatInput from "components/ChatLog/ChatInput";
import StepsDialog from "components/ChatLog/Steps";
import Thought from "components/ChatLog/Thought";
import generateName from "names";
import {
  createConversation,
  getConversations,
  getConversation,
} from "requests";
import { UserContext, ConversationContext, SnackbarContext } from "contexts";
import {
  conversationsReducer,
  getCurrentConversation,
} from "conversationsReducer";

const Alert = forwardRef(function Alert(props, ref) {
  return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

function App() {
  const [username, setUsername] = useState("");

  const ws = useRef(null);
  useEffect(() => {
    const conn = () => {
      const wsurl = window.location.origin.replace(/^http/, "ws") + "/api/chat";
      console.debug("connecting to", wsurl);
      ws.current = new WebSocket(wsurl);
      ws.current.onmessage = (msg) => {
        // <https://react.dev/learn/queueing-a-series-of-state-updates>
        // <https://react.dev/learn/updating-arrays-in-state>
        try {
          const payload = JSON.parse(msg.data);
          switch (payload.type) {
            case "text":
              dispatch({
                type: "messageAdded",
                id: payload.conversation,
                message: {
                  id: payload.id,
                  from: payload.from,
                  content: payload.content,
                  intermediate_steps: payload.intermediate_steps,
                },
              });
              break;
            case "stream/start":
              dispatch({
                type: "messageAdded",
                id: payload.conversation,
                message: {
                  id: payload.id,
                  from: payload.from,
                  content: payload.content || "",
                },
              });
              break;
            case "stream/text":
              dispatch({
                type: "messageAppended",
                id: payload.conversation,
                message: {
                  id: payload.id,
                  from: payload.from,
                  content: payload.content,
                },
              });
              break;
            case "thought/start":
              setThoughtOpen(true);
              setThoughts("");
              break;
            case "thought/text":
              setThoughts((prevThought) => prevThought + payload.content);
              break;
            case "info/intermediate-steps":
              dispatch({
                type: "stepsAdded",
                id: payload.conversation,
                message: {
                  id: payload.id,
                  content: payload.intermediate_steps,
                },
              });
              break;
            case "error":
              setSnackbar({
                open: true,
                severity: "error",
                message: `Something goes wrong, please try again later:\n${payload.content}`,
              });
              break;
            default:
              console.debug("unknown message type", payload);
              break;
          }
        } catch (error) {
          console.debug("not a json message", msg);
        }
      };
      ws.current.onopen = () => {
        console.debug("connected to", wsurl);
      };
      ws.current.onclose = () => {
        console.log("connection closed, reconnecting...");
        setSnackbar({
          open: true,
          severity: "error",
          message: "connection closed, reconnecting...",
        });
        setTimeout(() => {
          conn();
        }, 10000);
      };
      ws.current.onerror = (err) => {
        console.error(
          `Socket encountered error: ${err.message}, Closing socket`
        );
        ws.current.close();
      };
    };
    conn();

    return () => {
      ws.current?.close();
    };
  }, [ws]);

  const sendMessage = async (convId, message) => {
    ws.current?.send(
      JSON.stringify({
        conversation: convId,
        from: username,
        content: message,
        type: "text",
      })
    );
  };

  /**
   * All conversations of the current user.
   */
  const [conversations, dispatch] = useReducer(
    conversationsReducer,
    /** @type {[{id: string, title: string?, messages: Array, active: boolean}]} */
    []
  );

  const [currentConv, setCurrentConv] = useState(
    /** @type {{id: string, title: string?, messages: Array}} */ {}
  );
  useEffect(() => {
    if (conversations?.length > 0) {
      const currentConv = getCurrentConversation(conversations);
      setCurrentConv(currentConv);
    }
  }, [conversations]);

  const [thoughtOpen, setThoughtOpen] = useState(false);
  const [thoughts, setThoughts] = useState("");

  const [steps, setSteps] = useState([]);
  const [stepsDialogOpen, setStepsDialogOpen] = useState(false);

  const onStepsClick = async (message) => {
    setSteps(message.intermediate_steps);
    setStepsDialogOpen(true);
  };

  // initialization
  useEffect(() => {
    const initialization = async () => {
      let _username;
      const res = await fetch("/api/userinfo");
      if (res.ok) {
        const data = await res.json();
        if (data.username) {
          _username = data.username;
        } else {
          _username = generateName();
        }
      } else {
        console.error("error getting userinfo, generating fake user", res);
        _username = generateName();
      }
      setUsername(_username);

      let convs = await getConversations();
      if (convs.length > 0) {
        dispatch({
          type: "replaceAll",
          conversations: convs,
        });
      } else {
        console.log("no chats, initializing a new one");
        const conv = await createConversation();
        dispatch({
          type: "added",
          conversation: conv,
        });
        convs = [conv];
      }

      const activated = convs[0];
      const detailedConv = await getConversation(activated.id);
      dispatch({
        type: "updated",
        conversation: {
          ...detailedConv,
          messages: detailedConv.messages,
        },
      });
    };

    initialization();

    return () => {};
  }, []);

  /**
   * open, severity, message
   */
  const [snackbar, setSnackbar] = useState(
    /** @type {{open: boolean, severity: string?, message: string}} */ {}
  );

  const closeSnackbar = (event, reason) => {
    if (reason === "clickaway") {
      return;
    }
    setSnackbar({ ...snackbar, open: false });
  };

  return (
    <div className="App">
      <SnackbarContext.Provider value={setSnackbar}>
        <UserContext.Provider value={username}>
          <ConversationContext.Provider value={{ conversations, dispatch }}>
            <SideMenu />
            <section className="chatbox">
              <Thought
                open={thoughtOpen}
                onClose={() => setThoughtOpen(false)}
                content={thoughts}
              />
              <StepsDialog
                steps={steps}
                open={stepsDialogOpen}
                onClose={() => setStepsDialogOpen(false)}
              />
              <ChatLog>
                {currentConv?.messages?.map((message, index) => (
                  <ChatMessage
                    key={index}
                    message={message}
                    onStepsClick={() => onStepsClick(message)}
                  />
                ))}
              </ChatLog>
              <ChatInput chatId={currentConv?.id} onSend={sendMessage} />
            </section>
          </ConversationContext.Provider>
        </UserContext.Provider>
      </SnackbarContext.Provider>
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={closeSnackbar}
      >
        <Alert
          severity={snackbar.severity}
          sx={{ width: "100%" }}
          onClose={closeSnackbar}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </div>
  );
}

export default App;
