import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import StepContent from '@mui/material/StepContent';
import Typography from '@mui/material/Typography';


const getThought = (actionLog) => {
  return actionLog.substring(0, actionLog.indexOf("Action")).trim();
};

const stringfyResult = (result) => {
  if (typeof result === "string") {
    return result.trim();
  }
  return JSON.stringify(result);
}

/**
 * 
 * @param {object} props
 * @param {object} props.steps
 * @param {object} props.open
 * @param {object} props.onClose
 * @returns 
 */
export default function StepsDialog(props) {
  return (
    <Dialog
      open={props.open}
      onClose={props.onClose}
      scroll="paper"
      aria-labelledby="scroll-dialog-title"
      aria-describedby="scroll-dialog-description"
    >
      <DialogTitle id="scroll-dialog-title">Intermediate Steps</DialogTitle>
      <DialogContent dividers={true}>
        <Stepper orientation="vertical">
          {props.steps.map((step, index) => {
            const action = step[0];
            console.log("action", action)
            const result = step[1];
            console.log("result", result)
            return (
              <Step key={index} active={true}>
                <StepLabel>
                  {getThought(action.log)}
                </StepLabel>
                <StepContent>
                  <Typography>Action: {action.tool}</Typography>
                  <Typography>Action input: {action.tool_input}</Typography>
                  <Typography>Result: {stringfyResult(result)}</Typography>
                </StepContent>
              </Step>
            );
          })}
        </Stepper>
      </DialogContent>
    </Dialog>
  );
}
