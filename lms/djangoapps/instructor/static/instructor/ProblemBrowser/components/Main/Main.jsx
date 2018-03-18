import * as React from 'react';
import * as PropTypes from 'prop-types';
import {BlockBrowserContainer} from "../BlockBrowser/BlockBrowserContainer";

export default class Main extends React.Component {
    constructor(props) {
        super(props);
        this.handleToggleDropdown = this.handleToggleDropdown.bind(this);
        this.state = {
            showDropdown: false,
        };
    }

    handleToggleDropdown() {
        this.props.fetchCourseBlocks(this.props.courseId);
        this.setState({showDropdown: !this.state.showDropdown});
    }

    render() {
        const {selectedBlock, onSelectBlock} = this.props;

        return (
            <div className="problem-browser">
                <button onClick={this.handleToggleDropdown}>Select Problem</button>
                <input type="text" name="problem-location" value={selectedBlock} disabled/>
                {this.state.showDropdown &&
                <BlockBrowserContainer onSelectBlock={onSelectBlock}/>}
            </div>
        );
    }
}

Main.propTypes = {
    courseId: PropTypes.string.isRequired,
    fetchCourseBlocks: PropTypes.func.isRequired,
    onSelectBlock: PropTypes.func.isRequired,
    selectedBlock: PropTypes.string.isRequired,
};
