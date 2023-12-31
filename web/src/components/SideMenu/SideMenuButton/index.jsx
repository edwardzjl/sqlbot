import { useState, useEffect, useRef, useContext } from "react";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import { ClickAwayListener } from "@mui/base/ClickAwayListener";

import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DriveFileRenameOutlineIcon from "@mui/icons-material/DriveFileRenameOutline";
import CheckOutlinedIcon from "@mui/icons-material/CheckOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import { ConversationContext, SnackbarContext } from "contexts";
import { conversationsReducer, getConversationById } from "conversationsReducer";
import {
  createConversation,
  deleteConversation,
  getConversation,
  updateConversation,
} from "requests";

/**
 *
 * @param {Object} props
 * @param {Object} props.chat
 * @param {string} props.chat.id
 * @param {string} props.chat.title
 * @param {boolean} props.chat.active whether this chat is active
 * @returns
 */
const ChatTab = (props) => {
  const { conversations, dispatch } = useContext(ConversationContext);
  const setSnackbar = useContext(SnackbarContext);

  const [title, setTitle] = useState(props.chat?.title);
  useEffect(() => {
    setTitle(props.chat?.title);
  }, [props.chat?.title]);
  const titleRef = useRef(null);

  const [titleReadOnly, setTitleReadOnly] = useState(true);

  const [operationConfirm, setOperationConfirm] = useState(
    /** @type {[{onConfirm: boolean, operation: string}]} */ {
      onConfirm: false,
    }
  );

  const handleTitleChange = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setTitle(() => e.target.value);
  };

  const selectChat = async (e, chat) => {
    e.preventDefault();
    e.stopPropagation();
    if (chat.active) {
      return;
    }
    const detailedConv = await getConversation(chat.id);
    dispatch({
      type: "selected",
      data: detailedConv,
    });
  };

  const deleteChat = async (chatId) => {
    deleteConversation(chatId)
      .then(() => {
        const deleteAction = {
          type: "deleted",
          id: chatId,
        };
        const nextState = conversationsReducer(conversations, deleteAction);
        if (!nextState.length) {
          createConversation().then((data) => {
            dispatch(deleteAction);
            dispatch({
              type: "added",
              conversation: data,
            });
          });
        } else {
          // there's still conversations left, check if we are deleting the active one
          const toDelete = getConversationById(conversations, chatId);
          if (toDelete.active) {
            // switch to the first conversation
            // select before delete makes the page more smooth
            getConversation(nextState[0].id)
              .then((data) => {
                dispatch({
                  type: "selected",
                  data: data,
                });
              });
          }
          dispatch(deleteAction);
        }
        setSnackbar({
          open: true,
          severity: "success",
          message: "Chat deleted",
        });
      })
      .catch((err) => {
        console.error("error deleting chat", err);
        setSnackbar({
          open: true,
          severity: "error",
          message: "Delete chat failed",
        });
      });
  };

  const renameChat = async (id, title) => {
    setTitleReadOnly(true);
    updateConversation(id, title).then((res) => {
      if (res.ok) {
        setSnackbar({
          open: true,
          severity: "success",
          message: "Update chat success",
        });
      } else {
        console.error("error updating chat");
        setSnackbar({
          open: true,
          severity: "error",
          message: "Update chat failed",
        });
      }
    });
  };

  const onUpdateClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    titleRef.current.focus();
    setOperationConfirm({ onConfirm: true, operation: "rename" });
    setTitleReadOnly(false);
  };

  const onDeleteClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setOperationConfirm({ onConfirm: true, operation: "delete" });
  };

  const onConfirm = async (e, chatId) => {
    e.preventDefault();
    e.stopPropagation();
    if (operationConfirm.operation === "delete") {
      deleteChat(chatId);
    } else if (operationConfirm.operation === "rename") {
      renameChat(chatId, title);
    }
    setOperationConfirm({ onConfirm: false });
  };

  const onCancel = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setOperationConfirm({ onConfirm: false });
  };

  return (
    <div
      className={`sidemenu-button ${props.chat.active && "selected"}`}
      onClick={(e) => selectChat(e, props.chat)}
    >
      <Tooltip title={title}>
        <TextField
          id="chat-title"
          inputRef={titleRef}
          variant="standard"
          value={title}
          onChange={(e) => handleTitleChange(e)}
          sx={{
            maxWidth: 140,
          }}
          InputProps={{
            disableUnderline: true,
            readOnly: titleReadOnly,
          }}
          // TODO: migrate to css so we can use linear-gradient to fadeout long text
          // https://css-tricks.com/text-fade-read-more/
          inputProps={{
            style: {
              height: 10,
              color: "white",
            },
          }}
        />
      </Tooltip>

      <div className="sidemenu-button-operations">
        {/* Operations */}
        {!operationConfirm?.onConfirm && (
          <div>
            <DriveFileRenameOutlineIcon onClick={(e) => onUpdateClick(e)} />
            <DeleteOutlineIcon onClick={(e) => onDeleteClick(e)} />
          </div>
        )}
        {/* Confirmations */}
        {operationConfirm?.onConfirm && (
          <ClickAwayListener onClickAway={onCancel}>
            <div>
              <CheckOutlinedIcon onClick={(e) => onConfirm(e, props.chat.id)} />
              <CloseOutlinedIcon onClick={(e) => onCancel(e)} />
            </div>
          </ClickAwayListener>
        )}
      </div>
    </div>
  );
};

export default ChatTab;
