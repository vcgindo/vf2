import _ from 'lodash';
import React, { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { SET_TASK_PENDING_ROW_DATA } from '../../../../../redux/actions/MTO';

const CommentCellRenderer = (props: any) => {
  const detailTableRowData = useSelector((state: any) => state.mto.taskPendingRowData);
  const dispatch = useDispatch();
  const debouncedDispatch = useCallback(
    _.debounce((rowIndex: string, newComment: string) => {
      const newData = _.cloneDeep(detailTableRowData);
      newData[rowIndex].cm = newComment;
      dispatch(SET_TASK_PENDING_ROW_DATA(newData));
    }, 800),
    [detailTableRowData, dispatch]
  );

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newComment = e.target.value;
    debouncedDispatch(props.node.rowIndex, newComment);
  };

  return (
    <input
      onChange={onChange}
      defaultValue={props.data?.cm}
      type="text"
      placeholder="Enter comments if any"
      style={{ border: '0.5px solid black', fontSize: '12px', height: '24px', width: '100%' }}
    />
  );
};

export default CommentCellRenderer;
