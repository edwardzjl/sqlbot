import "./index.css";

import MuiAlert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";


/**
 * 
 * @param {object} props
 * @param {boolean} props.open
 * @param {object} props.onClose
 * @param {string} props.content
 * @returns 
 */
const Thought = (props) => {
  return (
    <Collapse in={props.open}>
      <MuiAlert
        severity="info"
        className="thought"
        action={
          <IconButton
            aria-label="close"
            color="inherit"
            size="small"
            onClick={props.onClose}
          >
            <CloseIcon fontSize="inherit" />
          </IconButton>
        }
      >
        {`Thought: ${props.content}`}
      </MuiAlert>
    </Collapse>
  );
};

export default Thought;
